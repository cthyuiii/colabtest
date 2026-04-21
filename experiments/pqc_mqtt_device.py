import argparse
import base64
import hashlib
import json
import os
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pqcrypto.kem.ml_kem_512 import encrypt


def derive_aes_key(shared_secret: bytes) -> bytes:
    return hashlib.sha256(shared_secret).digest()


class PQCDevice:
    def __init__(self, broker_host: str, broker_port: int, total_messages: int, rekey_every: int, delay: float):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.total_messages = total_messages
        self.rekey_every = rekey_every
        self.delay = delay

        self.topic_pubkey = "pqc_demo/pubkey"
        self.topic_handshake = "pqc_demo/handshake"
        self.topic_data = "pqc_demo/data"

        self.server_public_key = None
        self.aes_key = None
        self.aesgcm = None

        self.seq = 0
        self.encapsulation_times_ms = []
        self.encrypt_times_ms = []

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"[DEVICE] Connected to broker with rc={rc}")
        client.subscribe(self.topic_pubkey)

    def on_message(self, client, userdata, msg):
        if msg.topic == self.topic_pubkey:
            self.server_public_key = base64.b64decode(msg.payload)
            print("[DEVICE] Received retained ML-KEM-512 public key")

    def do_handshake(self):
        if self.server_public_key is None:
            raise RuntimeError("Server public key not received")

        t0 = time.perf_counter_ns()
        ciphertext, shared_secret = encrypt(self.server_public_key)
        t1 = time.perf_counter_ns()

        device_encaps_ms = (t1 - t0) / 1e6
        self.encapsulation_times_ms.append(device_encaps_ms)

        self.aes_key = derive_aes_key(shared_secret)
        self.aesgcm = AESGCM(self.aes_key)

        packet = {
            "ct": base64.b64encode(ciphertext).decode(),
            "device_encaps_ms": device_encaps_ms,
            "sent_ns": time.perf_counter_ns(),
        }

        self.client.publish(self.topic_handshake, json.dumps(packet))
        print(f"\n[DEVICE] Sent handshake")
        print(f"  Encapsulation: {device_encaps_ms:.3f} ms")

    def send_message(self):
        self.seq += 1

        if (self.seq - 1) % self.rekey_every == 0 and self.seq != 1:
            self.do_handshake()
            time.sleep(0.2)

        message = f"seq={self.seq} temp={20 + (self.seq % 10)}.5C humidity={60 + (self.seq % 10)}%"
        nonce = os.urandom(12)

        t0 = time.perf_counter_ns()
        ciphertext = self.aesgcm.encrypt(nonce, message.encode(), associated_data=None)
        t1 = time.perf_counter_ns()

        device_encrypt_ms = (t1 - t0) / 1e6
        self.encrypt_times_ms.append(device_encrypt_ms)

        packet = {
            "seq": self.seq,
            "nonce": base64.b64encode(nonce).decode(),
            "ct": base64.b64encode(ciphertext).decode(),
            "device_encrypt_ms": device_encrypt_ms,
        }

        self.client.publish(self.topic_data, json.dumps(packet))
        print(f"[DEVICE] Published seq={self.seq}")
        print(f"  Plaintext: {message}")
        print(f"  Encrypt: {device_encrypt_ms:.3f} ms")

    def run(self):
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

        start = time.time()
        while self.server_public_key is None and (time.time() - start) < 10:
            time.sleep(0.1)

        if self.server_public_key is None:
            raise RuntimeError("Did not receive server public key. Start server first.")

        self.do_handshake()

        for _ in range(self.total_messages):
            self.send_message()
            time.sleep(self.delay)

        self.client.loop_stop()
        self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="PQC MQTT device using ML-KEM-512")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--messages", type=int, default=20)
    parser.add_argument("--rekey-every", type=int, default=5)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    device = PQCDevice(args.host, args.port, args.messages, args.rekey_every, args.delay)
    device.run()


if __name__ == "__main__":
    main()