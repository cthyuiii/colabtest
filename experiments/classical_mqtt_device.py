import argparse
import base64
import hashlib
import json
import os
import time

import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_aes_key(shared_secret: bytes) -> bytes:
    return hashlib.sha256(shared_secret).digest()


class ClassicalDevice:
    def __init__(self, broker_host: str, broker_port: int, total_messages: int):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.total_messages = total_messages

        self.topic_pubkey = "classical_demo/pubkey"
        self.topic_handshake = "classical_demo/handshake"
        self.topic_data = "classical_demo/data"

        self.server_public_key = None
        self.private_key = X25519PrivateKey.generate()
        self.aes_key = None
        self.aesgcm = None

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"[CLASSICAL DEVICE] Connected rc={rc}")
        client.subscribe(self.topic_pubkey)

    def on_message(self, client, userdata, msg):
        if msg.topic == self.topic_pubkey:
            self.server_public_key = base64.b64decode(msg.payload)
            print("[CLASSICAL DEVICE] Received server X25519 public key")

    def do_handshake(self):
        peer_key = X25519PublicKey.from_public_bytes(self.server_public_key)

        t0 = time.perf_counter_ns()
        shared_secret = self.private_key.exchange(peer_key)
        t1 = time.perf_counter_ns()

        self.aes_key = derive_aes_key(shared_secret)
        self.aesgcm = AESGCM(self.aes_key)

        pub_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        packet = {
            "peer_pub": base64.b64encode(pub_bytes).decode(),
            "device_exchange_ms": (t1 - t0) / 1e6,
        }
        self.client.publish(self.topic_handshake, json.dumps(packet))
        print(f"[CLASSICAL DEVICE] Handshake sent. Exchange time={(t1 - t0)/1e6:.3f} ms")

    def run(self):
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

        start = time.time()
        while self.server_public_key is None and (time.time() - start) < 10:
            time.sleep(0.1)

        if self.server_public_key is None:
            raise RuntimeError("Did not receive classical server public key")

        self.do_handshake()

        for i in range(1, self.total_messages + 1):
            message = f"classical seq={i} temp={20 + i}.5C"
            nonce = os.urandom(12)
            ciphertext = self.aesgcm.encrypt(nonce, message.encode(), associated_data=None)

            packet = {
                "seq": i,
                "nonce": base64.b64encode(nonce).decode(),
                "ct": base64.b64encode(ciphertext).decode(),
            }
            self.client.publish(self.topic_data, json.dumps(packet))
            print(f"[CLASSICAL DEVICE] Sent seq={i}")
            time.sleep(1)

        self.client.loop_stop()
        self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Classical MQTT device using X25519")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--messages", type=int, default=10)
    args = parser.parse_args()

    ClassicalDevice(args.host, args.port, args.messages).run()


if __name__ == "__main__":
    main()