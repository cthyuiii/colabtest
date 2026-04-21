import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from pqcrypto.kem.ml_kem_512 import generate_keypair, encrypt


def measure_pqc():
    public_key, secret_key = generate_keypair()
    ciphertext, shared_secret = encrypt(public_key)

    packet = {
        "ct": base64.b64encode(ciphertext).decode(),
        "shared_hint": hashlib.sha256(shared_secret).hexdigest()[:16],
    }
    payload = json.dumps(packet).encode()

    return {
        "mode": "ML-KEM-512",
        "public_key_bytes": len(public_key),
        "ciphertext_bytes": len(ciphertext),
        "payload_bytes": len(payload),
    }


def measure_x25519():
    private_key = X25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes_raw()

    packet = {
        "peer_pub": base64.b64encode(public_key).decode(),
    }
    payload = json.dumps(packet).encode()

    return {
        "mode": "X25519",
        "public_key_bytes": len(public_key),
        "ciphertext_bytes": 0,
        "payload_bytes": len(payload),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark approximate handshake byte sizes")
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / "bytes_results.csv"

    rows = [measure_pqc(), measure_x25519()]

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["mode", "public_key_bytes", "ciphertext_bytes", "payload_bytes"]
        )
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(row)

    print(f"\nSaved results to {csv_path}")


if __name__ == "__main__":
    main()