markdown
# 🏠 G-Guard Smart Home Automation Hub

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Kivy](https://img.shields.io/badge/Kivy-34495E?style=for-the-badge&logo=python&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-660066?style=for-the-badge&logo=mqtt&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)

G-Guard is a full-stack, decoupled smart home automation system designed to control headless IR nodes (like TVs, AC units, and Gate Motors) via MQTT. It features a custom Android Material Design application, a persistent headless Linux scheduling server, and global remote access without requiring a VPN.

---

## 🏗️ System Architecture

The project is split into three highly decoupled layers, allowing the server to run autonomously even if the mobile app is offline.

1. **Frontend (Android App):** Built entirely in Python using **Kivy** and **KivyMD**. It provides a live MQTT remote control and a dynamic UI to build, view, and delete automated schedules.
2. **Backend (Ubuntu Server):** A headless **FastAPI** server that runs persistently as a `systemctl` background service. It stores user rules in **SQLite** and uses **APScheduler** to execute precise, CRON-style time triggers.
3. **IoT Layer (ESP8266 nodes):** Microcontrollers subscribed to an EMQX broker that translate the server's MQTT payloads into physical IR or relay signals.

---

## ✨ Key Features

* **Live Remote Control:** A full digital D-Pad, media controls, and quick-launch buttons that publish instantly to the MQTT broker.
* **Headless Background Scheduling:** Rules are stored in SQLite and loaded into a background clock on server startup. The server handles the execution, meaning the Android app does not need to be running for alarms to trigger.
* **Macro Command Sequences:** The engine supports chained commands with built-in delays (e.g., `POWER, WAIT_8, CH_5`). This solves the "boot-up delay" problem when turning on a TV and navigating to a specific channel.
* **Global Access via Ngrok:** Integrated `pyngrok` directly into the FastAPI lifespan events. The server automatically establishes a static global domain on boot, allowing the Android app to sync schedules from any network in the world.
* **Day-of-Week Mapping:** Custom UI logic to select specific days (e.g., `Su • Mo`) which translates dynamically into server-side Cron parameters.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Mobile UI** | `Kivy`, `KivyMD` | Cross-platform Python UI framework implementing Material Design. |
| **App Compiler**| `Buildozer` | Packages the Python code into a native `.apk` with Android SDK/NDK. |
| **API Gateway** | `FastAPI`, `Uvicorn`| High-performance async REST framework handling JSON payloads. |
| **Database** | `SQLite3` | Lightweight, file-based SQL storage for rule persistence. |
| **Task Engine** | `APScheduler` | Advanced background job scheduler for exact-time executions. |
| **Networking** | `pyngrok` | Python wrapper for Ngrok to tunnel localhost to a static web domain. |
| **Messaging** | `paho-mqtt` | Universal protocol used to communicate with ESP8266 endpoints. |

---

## 🚀 Installation & Setup

### 1. Backend Server Setup (Ubuntu/Linux)
Clone the repository to your home server and set up the Python virtual environment:

```bash
# Clone the repository
git clone [https://github.com/HashemAlsharif/g-guard-automation.git](https://github.com/HashemAlsharif/g-guard-automation.git)
cd g-guard-automation/server

# Set up the environment
python3 -m venv backend_venv
source backend_venv/bin/activate
pip install -r requirements.txt

```

Set your Ngrok authentication token securely:

```bash
export NGROK_AUTH_TOKEN="your_token_here"

```

To run the server permanently, edit the provided `automation-hub.service` file with your exact user paths, and enable it via `systemd`:

```bash
sudo cp automation-hub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now automation-hub.service

```

### 2. Frontend App Setup (Android)

Navigate to the `app` directory and update the `main.py` configuration to match your Ngrok static domain and MQTT broker IP.

```python
# main.py configuration
BROKER_IP = "broker.emqx.io"  
TOPIC = "hash/tvctl"
SERVER_IP = "[https://your-static-domain.ngrok-free.app](https://your-static-domain.ngrok-free.app)"

```

Connect your Android device via USB, enable USB debugging, and compile the application:

```bash
buildozer android debug deploy run

```

---

## 📡 API Endpoints

The FastAPI server exposes the following REST routes for the mobile app:

* `GET /api/schedules` - Fetches all saved rules from SQLite to populate the app UI.
* `POST /api/schedule/add` - Accepts a JSON payload (time, days, action), saves it to the DB, and injects it into the live APScheduler clock.
* `DELETE /api/schedule/{rule_id}` - Removes the rule from the database and kills the active background timer.

---

## 🔮 Future Roadmap

* **Hardware State Feedback:** Implement a USB 5V logic read on the ESP8266 to determine if the TV is physically powered on, preventing the "Toggle Problem" during automated macro executions.
* **Bluetooth Dynamo Gate Integration:** Expanding the ecosystem to include a bicycle-powered charging circuit to control the outdoor gate system via BLE.

---

**Author:** Hashem Alsharif
**Institution:** Al Hussein Technical University (Electrical Engineering)
