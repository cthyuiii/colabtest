import base64
import json
import hashlib
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import paho.mqtt.client as mqtt

from pqcrypto.kem.ml_kem_512 import generate_keypair, decrypt

BROKER_HOST = "localhost"
BROKER_PORT = 1883

TOPIC_PUBKEY = "pqc_demo/pubkey"
TOPIC_HANDSHAKE = "pqc_demo/handshake"
TOPIC_DATA = "pqc_demo/data"

# Server generates KEM keypair once at startup (can also rotate keys if you want)
public_key, secret_key = generate_keypair()
aes_key = None

# Stats
handshake_count = 0
msg_count = 0
dec_times_ms = []
decrypt_times_ms = []

def derive_aes_key(shared_secret: bytes) -> bytes:
    return hashlib.sha256(shared_secret).digest()  # AES-256 key

def on_connect(client, userdata, flags, rc):
    print("Connected with result code:", rc)
    client.subscribe([(TOPIC_HANDSHAKE, 0), (TOPIC_DATA, 0)])

    # Retain pubkey so device gets it even if it subscribes later
    payload = base64.b64encode(public_key).decode()
    client.publish(TOPIC_PUBKEY, payload, retain=True)
    print("Published (retained) server public key to:", TOPIC_PUBKEY)

def on_message(client, userdata, msg):
    global aes_key, handshake_count, msg_count

    if msg.topic == TOPIC_HANDSHAKE:
        packet = json.loads(msg.payload.decode())

        ct = base64.b64decode(packet["ct"])
        t_device_ms = packet.get("t_encaps_ms", None)
        sent_ns = packet.get("sent_ns", None)

        # Server decapsulation timing
        t0 = time.perf_counter_ns()
        shared_secret = decrypt(secret_key, ct)
        t1 = time.perf_counter_ns()
        t_dec_ms = (t1 - t0) / 1e6
        dec_times_ms.append(t_dec_ms)

        aes_key = derive_aes_key(shared_secret)
        handshake_count += 1

        now_ns = time.perf_counter_ns()
        e2e_ms = (now_ns - sent_ns) / 1e6 if sent_ns else None

        print(f"\n=== HANDSHAKE #{handshake_count} COMPLETE ===")
        if t_device_ms is not None:
            print(f"Device encapsulation time: {t_device_ms:.3f} ms")
        print(f"Server decapsulation time: {t_dec_ms:.3f} ms")
        if e2e_ms is not None:
            print(f"Approx handshake e2e (device->server): {e2e_ms:.3f} ms")

        print(f"Avg server decap time so far: {sum(dec_times_ms)/len(dec_times_ms):.3f} ms")

    elif msg.topic == TOPIC_DATA:
        if aes_key is None:
            print("Got data before handshake. Ignoring.")
            return

        packet = json.loads(msg.payload.decode())
        nonce = base64.b64decode(packet["nonce"])
        ct = base64.b64decode(packet["ct"])
        t_enc_ms = packet.get("t_encrypt_ms", None)
        seq = packet.get("seq", None)

        aesgcm = AESGCM(aes_key)

        # Server decrypt timing
        t0 = time.perf_counter_ns()
        plaintext = aesgcm.decrypt(nonce, ct, associated_data=None)
        t1 = time.perf_counter_ns()
        t_dec_ms = (t1 - t0) / 1e6
        decrypt_times_ms.append(t_dec_ms)

        msg_count += 1
        text = plaintext.decode(errors="replace")

        print(f"[MSG seq={seq}] {text}")
        if t_enc_ms is not None:
            print(f"  Device encrypt time: {t_enc_ms:.3f} ms")
        print(f"  Server decrypt time: {t_dec_ms:.3f} ms")

        if msg_count % 5 == 0:
            avg_dec = sum(decrypt_times_ms) / len(decrypt_times_ms)
            print(f"\n--- Stats after {msg_count} messages ---")
            print(f"Avg server decrypt time: {avg_dec:.3f} ms")
            if dec_times_ms:
                print(f"Avg server decap time: {sum(dec_times_ms)/len(dec_times_ms):.3f} ms")
            print("--------------------------------------\n")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()