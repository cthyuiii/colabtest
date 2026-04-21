# PQC IoT MQTT Prototype

A MacBook-friendly prototype for replicating the **transport-security** part of a post-quantum IoT architecture project.

This repository focuses on the gateway ↔ network-server style communication path using:

- **ML-KEM-512** for post-quantum key establishment
- **X25519** as a classical baseline
- **AES-GCM** for payload encryption
- **MQTT (Mosquitto)** for message transport
- benchmark scripts for:
  - handshake latency
  - approximate handshake byte size

This is a practical local replication of the final report’s secure transport and measurement workflow, without requiring the full LoRaWAN hardware lab setup.

---

## Features

- PQC MQTT demo using **ML-KEM-512**
- Classical MQTT demo using **X25519**
- AES-GCM encrypted payload exchange
- Rekeying every `N` messages in PQC mode
- Handshake benchmark with CSV output
- Approximate byte-size benchmark with CSV output
- Jupyter notebook for result inspection

---

## How it works

### PQC mode
	1.	The server generates an ML-KEM-512 keypair
	2.	The server publishes its public key to MQTT
	3.	The device receives the server public key
	4.	The device encapsulates a shared secret using ML-KEM-512
	5.	The device sends the ciphertext to the server
	6.	The server decapsulates the ciphertext
	7.	Both sides derive the same AES key
	8.	The device encrypts messages using AES-GCM
	9.	The server decrypts and prints the plaintext

### Classical mode

	The same workflow is reproduced using X25519 for key agreement so that classical and post-quantum behavior can be compared.

## Repository structure

```text
pqc-iot/
├── experiments/
│   ├── pqc_mqtt_device.py
│   ├── pqc_mqtt_server.py
│   ├── classical_mqtt_device.py
│   ├── classical_mqtt_server.py
│   ├── benchmark_handshake.py
│   └── benchmark_bytes.py
├── results/
│   └── .gitkeep
├── notebooks/
│   └── analysis.ipynb
├── requirements.txt
└── README.md
```

## Installtion 

```
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### macos / linux
```
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (Command Prompt)

```
python -m venv .venv
.venv\Scripts\activate
```

### Update Pip

```
python -m pip install --upgrade pip
```

### Install Python dependencies

```
pip install -r requirements.txt
```

### Install Mosquitto MQTT Broker (Macos)

```
brew install mosquitto
mosquitto
```

### Install Mosquitto MQTT Broker (Linux)

```
sudo apt update
sudo apt install mosquitto mosquitto-clients
mosquitto
```

### Install Mosquitto MQTT Broker (Windows)

```
https://mosquitto.org
mosquitto
```

## Running the PQC MQTT demo

### Terminal 1 — Start Mosquitto

```
mosquitto
```

### Terminal 2 — Start PQC server

```
python experiments/pqc_mqtt_server.py
```

### Terminal 3 — Start PQC device

```
python experiments/pqc_mqtt_device.py --messages 20 --rekey-every 5
```

## Running the classical MQTT demo

### Terminal 1 — Start Mosquitto

```
mosquitto
```

### Terminal 2 — Start classical server

```
python experiments/classical_mqtt_server.py
```

### Terminal 3 — Start classical device

```
python experiments/classical_mqtt_device.py --messages 10
```

## Running the benchmarks

### Handshake latency benchmark

```
python experiments/benchmark_handshake.py --iterations 100
```

### Approximate byte-size benchmark

```
python experiments/benchmark_bytes.py
```
