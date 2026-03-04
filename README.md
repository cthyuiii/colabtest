# EXPERIMENT FOR MQTT AND PQC

## Post-Quantum Cryptography MQTT Experiment

This repository demonstrates a Post-Quantum Cryptography (PQC) secure communication prototype for IoT messaging using ML-KEM-512 (Kyber) and MQTT.

The project simulates an IoT device communicating securely with a server using:
	•	ML-KEM-512 → Post-Quantum key exchange
	•	AES-GCM → Symmetric encryption for message payloads
	•	MQTT (Mosquitto) → Messaging protocol
  
The experiment includes benchmarking and re-keying policies to evaluate performance overhead of PQC in IoT communication systems.

### Architecture
IoT Device (Publisher) → ML-KEM-512 Key Encapsulation → MQTT Broker (Mosquitto) → Server (Subscriber)

### Communication workflow:
	1.	Server generates ML-KEM public/private keypair
	2.	Server publishes public key via MQTT
	3.	Device receives public key
	4.	Device performs ML-KEM encapsulation to create shared secret
	5.	Device sends ciphertext to server
	6.	Server decapsulates to recover shared secret
	7.	Both derive AES-256 session key
	8.	Device sends encrypted MQTT messages
	9.	Server decrypts messages


### File - Purpose<br>
server_subscriber.py - Simulates IoT server receiving encrypted MQTT messages<br>
device_publisher.py - Simulates IoT device sending encrypted messages<br>
pqc_mqtt_experiment.ipynb - Notebook demonstrating PQC experiments<br>

## Installation Guide
This project requires:<br>
	•	Python 3.9+<br>
	•	Mosquitto MQTT broker<br>
	•	Python packages for PQC and MQTT communication<br>

The installation steps differ slightly depending on your operating system.

### 1. Install Mosquitto MQTT Broker

#### macOS (Homebrew)
  Install Mosquitto using Homebrew:<br>
   ```
   brew install mosquitto
```

  Start the broker:<br>
  ```
  mosquitto
```

  Run Mosquitto as a background service:<br>
```
brew services start mosquitto
```

  Stop the service:<br>
```
brew services stop mosquitto
```

#### Windows
 Download Mosquitto from:<br>
```
https://mosquitto.org/download/
```
  
 Install Mosquitto and enable:<br>
```
Install Service
Install Broker
```

Start the broker from Command Prompt:<br>
```
mosquitto
```

#### Linux (Ubuntu / Debian)

Install Mosquitto:
```
sudo apt update
sudo apt install mosquitto mosquitto-clients 
```
  Start the broker:<br>
```
sudo systemctl start mosquitto
```

  Enable Mosquitto to run automatically on startup:<br>
  ```
  sudo systemctl enable mosquitto
```

  Check broker status:<br>
  ```
  sudo systemctl status mosquitto
```

Default broker address:<br>
```
localhost:1883
```

### 2. Verify MQTT Broker
You can test MQTT communication before running the experiment.  

Open two terminals.<br>

Terminal 1 (Subscriber)
```
mosquitto_sub -h localhost -t test/topic
```

Terminal 2 (Publisher)
```
mosquitto_pub -h localhost -t test/topic -m "Hello MQTT"
```

If everything works, Terminal 1 should display:
```
Hello MQTT
```

### 3. Clone Repository
```
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 4. Install Python Dependencies

macOS / Linux
```
pip install -r requirements.txt
```

Windows

Run in Command Prompt or PowerShell:
```
pip install -r requirements.txt
```

### 5. Run the Experiment

Open three terminals.<br>

Terminal 1 — Start MQTT Broker
```
mosquitto
```

Terminal 2 — Start Server
```
python experiments/server_subscriber.py
```

Terminal 3 — Start Device
```
python experiments/device_publisher.py
```

### Troubleshooting

#### MQTT broker not running<br>

Check if port 1883 is active:<br>
macOS / Linux
```
lsof -i :1883
```
Windows
```
netstat -ano | findstr 1883
```

#### Device does not receive public key
Ensure the server is started before the device.

#### Python dependency issues

Upgrade pip:
```
pip install --upgrade pip
```
