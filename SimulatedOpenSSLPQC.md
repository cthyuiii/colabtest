# Post-Quantum Cryptography (PQC) Environment Simulation

## Overview
This Google Collab notebook simulates the deployment of NIST-standardized Post-Quantum Cryptography (PQC) within a secure cloud environment. It bypasses physical edge-hardware constraints (like ARM toolchain mismatches or thermal throttling) to allow for rapid compilation and benchmarking of lattice-based algorithms, specifically ML-KEM.

The architecture relies on compiling the Open Quantum Safe (`liboqs`) C library from source and linking it to the system's native cryptography via the `oqs-provider` OpenSSL bridge.

---

## Phase 1: Securing the Build Environment
Before pulling any cryptographic libraries, the Linux instance must be equipped with the correct C compilers and build systems. We utilize `ninja-build` over standard `make` to significantly accelerate the compilation process.

```bash
!sudo apt-get update
!sudo apt-get install cmake gcc ninja-build libssl-dev git build-essential -y
```

## Phase 2: Compiling the Quantum Core (liboqs)
The liboqs repository contains the highly optimized C implementations of post-quantum algorithms. This phase pulls the source code, configures the build system for the current CPU architecture, and installs the compiled binaries into the system.

```bash
!git clone https://github.com/open-quantum-safe/liboqs.git
%cd liboqs
!mkdir build
%cd build
!cmake -GNinja ..
!ninja
!sudo ninja install
%cd /content
```

## Phase 3: Building the OpenSSL Bridge (oqs-provider)
Standard OpenSSL does not natively understand quantum algorithms. The oqs-provider acts as a translation layer, allowing OpenSSL to utilize the liboqs math we just compiled. We explicitly point the compiler to the system's root OpenSSL directory.

```bash
!git clone https://github.com/open-quantum-safe/oqs-provider.git
%cd oqs-provider
!mkdir build
%cd build
!cmake -DOPENSSL_ROOT_DIR=/usr -GNinja ..
!ninja
%cd /content
```

## Phase 4: Execution and Benchmarking
With the provider compiled, we can benchmark the cryptographic throughput (Keygen, Encapsulation, Decapsulation).

### Option A: The OpenSSL Benchmark
We must export the OPENSSL_MODULES environment variable so OpenSSL knows exactly where our custom bridge is located before running the speed command.

```bash
!export OPENSSL_MODULES=/content/oqs-provider/build/lib && \
 openssl speed -provider oqsprovider -provider default mlkem512
```

### Option B: The Native Fallback Benchmark
If OpenSSL throws an Unknown algorithm error due to naming convention shifts (e.g., mlkem512 vs. kyber512), we bypass the OpenSSL provider entirely and use the native speed_kem tool compiled directly within liboqs.

To benchmark all algorithms:
```bash
!/content/liboqs/build/tests/speed_kem
```

To target a specific algorithm:
```bash
!/content/liboqs/build/tests/speed_kem ML-KEM-512
```