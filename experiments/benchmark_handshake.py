import argparse
import csv
import statistics
import time
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from pqcrypto.kem.ml_kem_512 import generate_keypair, encrypt, decrypt


def benchmark_pqc(iterations: int):
    results = []

    for _ in range(iterations):
        public_key, secret_key = generate_keypair()

        t0 = time.perf_counter_ns()
        ciphertext, shared_secret_1 = encrypt(public_key)
        shared_secret_2 = decrypt(secret_key, ciphertext)
        t1 = time.perf_counter_ns()

        assert shared_secret_1 == shared_secret_2
        results.append((t1 - t0) / 1e6)

    return results


def benchmark_x25519(iterations: int):
    results = []

    for _ in range(iterations):
        server_private = X25519PrivateKey.generate()
        server_public = server_private.public_key()

        client_private = X25519PrivateKey.generate()
        client_public = client_private.public_key()

        t0 = time.perf_counter_ns()
        ss1 = client_private.exchange(server_public)
        ss2 = server_private.exchange(client_public)
        t1 = time.perf_counter_ns()

        assert ss1 == ss2
        results.append((t1 - t0) / 1e6)

    return results


def summarize(name: str, values):
    p50 = statistics.quantiles(values, n=100)[49]
    p90 = statistics.quantiles(values, n=100)[89]
    avg = statistics.mean(values)
    print(f"{name}")
    print(f"  avg={avg:.3f} ms")
    print(f"  p50={p50:.3f} ms")
    print(f"  p90={p90:.3f} ms")


def write_csv(path: Path, mode: str, values):
    exists = path.exists()
    with path.open("a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["mode", "iteration", "handshake_ms"])
        for i, v in enumerate(values, start=1):
            writer.writerow([mode, i, f"{v:.6f}"])


def main():
    parser = argparse.ArgumentParser(description="Benchmark handshake latency for PQC and classical modes")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / "handshake_results.csv"

    pqc_results = benchmark_pqc(args.iterations)
    classical_results = benchmark_x25519(args.iterations)

    summarize("ML-KEM-512", pqc_results)
    summarize("X25519", classical_results)

    write_csv(csv_path, "ML-KEM-512", pqc_results)
    write_csv(csv_path, "X25519", classical_results)

    print(f"\nSaved results to {csv_path}")


if __name__ == "__main__":
    main()