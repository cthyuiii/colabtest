import argparse
import base64
import hashlib
import json
import time

import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_aes_key(shared_secret: bytes) -> bytes:
    return hashlib.sha256(shared_secret).digest()


class ClassicalServer:
    def __init__(self, broker_host: str, broker_port: int):
        self.broker_host = broker_host
        self.broker_port = broker_port

        self.topic_pubkey = "classical_demo/pubkey"
        self.topic_handshake = "classical_demo/handshake"
        self.topic_data = "classical_demo/data"

        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.aes_key = None

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"[CLASSICAL SERVER] Connected rc={rc}")
        client.subscribe([(self.topic_handshake, 0), (self.topic_data, 0)])

        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        client.publish(self.topic_pubkey, base64.b64encode(pub_bytes).decode(), retain=True)
        print("[CLASSICAL SERVER] Published retained X25519 public key")

    def on_message(self, client, userdata, msg):
        if msg.topic == self.topic_handshake:
            packet = json.loads(msg.payload.decode())
            peer_pub = base64.b64decode(packet["peer_pub"])
            peer_key = X25519PublicKey.from_public_bytes(peer_pub)

            t0 = time.perf_counter_ns()
            shared_secret = self.private_key.exchange(peer_key)
            t1 = time.perf_counter_ns()

            self.aes_key = derive_aes_key(shared_secret)
            print(f"[CLASSICAL SERVER] Handshake complete. Exchange time={(t1 - t0)/1e6:.3f} ms")

        elif msg.topic == self.topic_data:
            if self.aes_key is None:
                print("[CLASSICAL SERVER] Data before handshake ignored")
                return

            packet = json.loads(msg.payload.decode())
            nonce = base64.b64decode(packet["nonce"])
            ciphertext = base64.b64decode(packet["ct"])

            aesgcm = AESGCM(self.aes_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            print(f"[CLASSICAL SERVER] {plaintext.decode(errors='replace')}")

    def run(self):
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_forever()


def main():
    parser = argparse.ArgumentParser(description="Classical MQTT server using X25519")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    ClassicalServer(args.host, args.port).run()


if __name__ == "__main__":
    main()