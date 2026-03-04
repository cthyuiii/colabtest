import base64
import json
import time
import hashlib
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import paho.mqtt.client as mqtt

from pqcrypto.kem.ml_kem_512 import encrypt

BROKER_HOST = "localhost"
BROKER_PORT = 1883

TOPIC_PUBKEY = "pqc_demo/pubkey"
TOPIC_HANDSHAKE = "pqc_demo/handshake"
TOPIC_DATA = "pqc_demo/data"

REKEY_EVERY = 5          # re-handshake every N messages
TOTAL_MESSAGES = 20      # total messages to send

server_public_key = None
aes_key = None
aesgcm = None
seq = 0

encaps_times_ms = []
encrypt_times_ms = []

def derive_aes_key(shared_secret: bytes) -> bytes:
    return hashlib.sha256(shared_secret).digest()

def do_handshake(client):
    """Encapsulate to server public key and publish ciphertext.
    Measures encapsulation timing.
    """
    global aes_key, aesgcm, encaps_times_ms

    # Device encapsulation timing
    t0 = time.perf_counter_ns()
    ciphertext, shared_secret = encrypt(server_public_key)
    t1 = time.perf_counter_ns()
    t_encaps_ms = (t1 - t0) / 1e6
    encaps_times_ms.append(t_encaps_ms)

    aes_key = derive_aes_key(shared_secret)
    aesgcm = AESGCM(aes_key)

    packet = {
        "ct": base64.b64encode(ciphertext).decode(),
        "t_encaps_ms": t_encaps_ms,
        "sent_ns": time.perf_counter_ns()
    }
    client.publish(TOPIC_HANDSHAKE, json.dumps(packet))
    print(f"\n=== DEVICE HANDSHAKE SENT ===")
    print(f"Encapsulation time: {t_encaps_ms:.3f} ms")
    print(f"Avg encaps time so far: {sum(encaps_times_ms)/len(encaps_times_ms):.3f} ms")

def on_connect(client, userdata, flags, rc):
    print("Connected with result code:", rc)
    client.subscribe(TOPIC_PUBKEY)

def on_message(client, userdata, msg):
    global server_public_key
    if msg.topic == TOPIC_PUBKEY:
        server_public_key = base64.b64decode(msg.payload)
        print("Received server public key.")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

client.loop_start()

# Wait for server public key (retained message should arrive quickly)
timeout_s = 10
start = time.time()
while server_public_key is None and (time.time() - start) < timeout_s:
    time.sleep(0.1)

if server_public_key is None:
    raise RuntimeError("Did not receive server public key. Is server running?")

# Initial handshake
do_handshake(client)

# Send messages with rekeying
for i in range(TOTAL_MESSAGES):
    seq += 1

    if (seq - 1) % REKEY_EVERY == 0 and seq != 1:
        # Rekey before sending this message
        do_handshake(client)
        time.sleep(0.2)  # tiny pause to let server process handshake

    message = f"seq={seq} temp={20 + (seq % 10)}.5C humidity={60 + (seq % 10)}%"
    nonce = os.urandom(12)

    # Encrypt timing
    t0 = time.perf_counter_ns()
    ct = aesgcm.encrypt(nonce, message.encode(), associated_data=None)
    t1 = time.perf_counter_ns()
    t_encrypt_ms = (t1 - t0) / 1e6
    encrypt_times_ms.append(t_encrypt_ms)

    packet = {
        "seq": seq,
        "nonce": base64.b64encode(nonce).decode(),
        "ct": base64.b64encode(ct).decode(),
        "t_encrypt_ms": t_encrypt_ms
    }
    client.publish(TOPIC_DATA, json.dumps(packet))
    print(f"[PUBLISHED seq={seq}] encrypt={t_encrypt_ms:.3f} ms  |  {message}")

    if seq % 5 == 0:
        print(f"--- Device stats after {seq} msgs ---")
        print(f"Avg encrypt time: {sum(encrypt_times_ms)/len(encrypt_times_ms):.3f} ms")
        print(f"Avg encaps time: {sum(encaps_times_ms)/len(encaps_times_ms):.3f} ms")
        print("----------------------------------")

    time.sleep(1)

client.loop_stop()
client.disconnect()