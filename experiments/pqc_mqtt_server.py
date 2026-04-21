import argparse
import base64
import hashlib
import json
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pqcrypto.kem.ml_kem_512 import generate_keypair, decrypt


def derive_aes_key(shared_secret: bytes) -> bytes:
    return hashlib.sha256(shared_secret).digest()


class PQCServer:
    def __init__(self, broker_host: str, broker_port: int, rekey_every: int, results_dir: str):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.rekey_every = rekey_every
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.topic_pubkey = "pqc_demo/pubkey"
        self.topic_handshake = "pqc_demo/handshake"
        self.topic_data = "pqc_demo/data"

        self.public_key, self.secret_key = generate_keypair()
        self.aes_key = None

        self.handshake_count = 0
        self.message_count = 0
        self.decapsulation_times_ms = []
        self.decrypt_times_ms = []

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"[SERVER] Connected to broker with rc={rc}")
        client.subscribe([(self.topic_handshake, 0), (self.topic_data, 0)])

        payload = base64.b64encode(self.public_key).decode()
        client.publish(self.topic_pubkey, payload, retain=True)
        print("[SERVER] Published retained ML-KEM-512 public key")

    def on_message(self, client, userdata, msg):
        if msg.topic == self.topic_handshake:
            self.handle_handshake(msg.payload)
        elif msg.topic == self.topic_data:
            self.handle_data(msg.payload)

    def handle_handshake(self, payload: bytes):
        packet = json.loads(payload.decode())
        ciphertext = base64.b64decode(packet["ct"])
        device_encaps_ms = packet.get("device_encaps_ms")
        device_sent_ns = packet.get("sent_ns")

        t0 = time.perf_counter_ns()
        shared_secret = decrypt(self.secret_key, ciphertext)
        t1 = time.perf_counter_ns()

        server_decaps_ms = (t1 - t0) / 1e6
        self.decapsulation_times_ms.append(server_decaps_ms)
        self.aes_key = derive_aes_key(shared_secret)
        self.handshake_count += 1

        approx_e2e_ms = None
        if device_sent_ns is not None:
            approx_e2e_ms = (time.perf_counter_ns() - device_sent_ns) / 1e6

        print(f"\n[SERVER] Handshake #{self.handshake_count} complete")
        if device_encaps_ms is not None:
            print(f"  Device encapsulation: {device_encaps_ms:.3f} ms")
        print(f"  Server decapsulation: {server_decaps_ms:.3f} ms")
        if approx_e2e_ms is not None:
            print(f"  Approx device->server handshake time: {approx_e2e_ms:.3f} ms")

    def handle_data(self, payload: bytes):
        if self.aes_key is None:
            print("[SERVER] Received encrypted data before handshake, ignoring")
            return

        packet = json.loads(payload.decode())
        nonce = base64.b64decode(packet["nonce"])
        ciphertext = base64.b64decode(packet["ct"])
        seq = packet.get("seq")
        device_encrypt_ms = packet.get("device_encrypt_ms")

        aesgcm = AESGCM(self.aes_key)

        t0 = time.perf_counter_ns()
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        t1 = time.perf_counter_ns()

        server_decrypt_ms = (t1 - t0) / 1e6
        self.decrypt_times_ms.append(server_decrypt_ms)
        self.message_count += 1

        print(f"[SERVER] seq={seq} plaintext={plaintext.decode(errors='replace')}")
        if device_encrypt_ms is not None:
            print(f"  Device encrypt: {device_encrypt_ms:.3f} ms")
        print(f"  Server decrypt: {server_decrypt_ms:.3f} ms")

    def run(self):
        print(f"[SERVER] Starting on {self.broker_host}:{self.broker_port}")
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_forever()


def main():
    parser = argparse.ArgumentParser(description="PQC MQTT server using ML-KEM-512")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--rekey-every", type=int, default=5)
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    server = PQCServer(args.host, args.port, args.rekey_every, args.results_dir)
    server.run()


if __name__ == "__main__":
    main()