# ADAM — Autonomous Desktop AI Module

<div align="center">

<img src="assets/images/adam-transparent.png" alt="ADAM Robot" width="280" />

### *Embodied Multimodal Intelligence on Your Desk*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/Gemini-Live%20Multimodal%20API-4285F4.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Hardware](https://img.shields.io/badge/Hardware-Pi%20Zero%202W%20%7C%20ESP32--CAM%20%7C%20RP2040-red.svg)](#hardware-architecture)
[![Made in India](https://img.shields.io/badge/Made%20in%20India-%F0%9F%87%AE%F0%9F%87%B3%20DGEN%20Technologies-orange.svg)](https://dgentechnologies.com)

[**Explore Docs**](docs/architecture/system-architecture.md) &nbsp;•&nbsp;
[**Hardware Setup**](docs/hardware/pinout.md) &nbsp;•&nbsp;
[**Software Stack**](software/pi/README.md) &nbsp;•&nbsp;
[**Companion Apps**](apps/README.md) &nbsp;•&nbsp;
[**Contributing**](CONTRIBUTING.md)

</div>

---

## 🌟 Overview

**ADAM (Autonomous Desktop AI Module)** is a next-generation, open-source embodied AI companion engineered by **[DGEN Technologies Pvt. Ltd.](https://dgentechnologies.com)** 

Unlike traditional smart speakers or screen-bound voice assistants, ADAM combines **cloud-scale multimodal intelligence** with **physical robotic embodiment**. Powered by the **Google Gemini Live API**, ADAM engages in natural, full-duplex conversational voice interactions with ultra-low latency, perceives visual context through an onboard vision sensor, tracks human presence mechanically using dual-microphone sound localization, and conveys rich emotional nuance through fluid vector-rendered digital eyes.

Whether acting as an autonomous desktop companion, an intelligent workstation orchestrator, or an extensible robotics research platform, ADAM bridges the physical and digital worlds seamlessly.

---

## ✨ Key Highlights & Capabilities

| Capability | Technical Realization |
| :--- | :--- |
| **Bidirectional Live Voice** | Full-duplex audio streaming over persistent WebSockets to **Gemini Multimodal Live**, featuring sub-second response times and immediate barge-in / interruption handling. |
| **Acoustic Localization (DOA)** | Dual I2S **INMP441** MEMS microphones running real-time **GCC-PHAT** cross-correlation algorithms to pinpoint speaker direction and turn toward voice sources. |
| **Expressive Animated Eyes** | Dedicated **Raspberry Pi Pico (RP2040)** rendering 60 FPS vector eye and mouth animations across 14 emotional states on a 2.4" **ST7789** IPS display. |
| **Vision & Duty-Cycled Optics** | Hardware-accelerated **ESP32-CAM (OV2640)** streaming compressed JPEG frames over high-speed UART (921,600 baud) with intelligent thermal duty-cycling. |
| **Capacitive Touch Matrix** | Four **TTP223** touch sensors (cheeks, head, chin) configured in momentary mode for petting, waking, and physical tap feedback. |
| **Pan-Tilt Mechanical Actuation** | Closed-loop servo actuation (Pan via Pi GPIO PWM, Tilt via ESP32) for expressive lifelike head gestures. |
| **Local Companion Agent** | Distributed LAN-based **Laptop Agent** exposing system controls (volume, brightness, application launching, Spotify) via self-describing REST and mDNS. |
| **Persistent Contextual Memory** | Local JSON & vector-backed long-term memory store allowing ADAM to recall personal user preferences, past conversations, and facts. |

---

## 🏛️ System Architecture

ADAM utilizes a **distributed micro-tier architecture** that offloads heavy computation to specialized processing units, ensuring real-time responsiveness without thermal throttling:

```
                                  ┌───────────────────────────┐
                                  │ Google Gemini Live Cloud  │
                                  │ (Bidirectional WebSockets)│
                                  └─────────────▲─────────────┘
                                                │ (WiFi / TLS)
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  TIER 1: RASPBERRY PI ZERO 2 W (Orchestration & Voice Brain)                                  │
│                                                                                                │
│   INMP441 Dual Mics ──▶ [arecord (S32_LE)] ──▶ [GCC-PHAT DSP] ──▶ Pan Servo (GPIO12)          │
│   Gemini Voice Out   ──▶ [aplay (S16_LE)]   ──▶ MAX98357A I2S Amp ──▶ 3W Speaker               │
│   Vosk Offline Engine (Wake-word) & Persistent Memory Store                                    │
└───────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                │ PL011 UART (/dev/serial0 @ 921,600 baud)
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  TIER 2: ESP32-CAM (Vision, Touch, Tilt & Peripheral Relay)                                   │
│                                                                                                │
│   OV2640 Camera ──▶ [Hardware JPEG] ──▶ UART2 ──▶ Sent to Pi                                  │
│   4x TTP223 Touch Pads ──▶ [Majority-Vote Debounce] ──▶ UART2 ──▶ Sent to Pi                  │
│   Tilt Servo ◀── GPIO13 PWM (Inbound TILT commands from Pi)                                    │
└───────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                │ UART1 (GPIO3 TX @ 115,200 baud, One-Way Relay)
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  TIER 3: RASPBERRY PI PICO RP2040 (Expressive Digital Face)                                    │
│                                                                                                │
│   Inbound Emotion Commands (ASCII: happy, idle, thinking, rizz, etc.)                          │
│   ST7789 2.4" 320x240 Display ◀── SPI Bus @ 40 MHz (Double-Buffered RGB565 Vector Engine)     │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

For complete technical specifications, see:
- [**System Architecture Specification**](docs/architecture/system-architecture.md)
- [**Data Flow & Protocol Breakdown**](docs/architecture/data-flow.md)
- [**Hardware & Power Distribution Architecture**](docs/architecture/hardware-architecture.md)

---

## 📁 Repository Structure

```text
ADAM AI/
├── README.md                            # Primary project landing page
├── LICENSE                              # Apache 2.0 open-source license
├── CONTRIBUTING.md                      # Contribution and coding guidelines
├── .gitignore                           # Git ignore rules for Python, C++, and builds
├── .env.example                         # Safe template for credentials & config
│
├── docs/                                # In-depth technical documentation
│   ├── architecture/
│   │   ├── system-architecture.md       # Multi-tier computing model & topology
│   │   ├── data-flow.md                 # End-to-end data lifecycle & protocols
│   │   └── hardware-architecture.md     # Power rails, buck regulators & thermals
│   ├── hardware/
│   │   ├── raspberry-pi.md              # Pi Zero 2 W bring-up, OS & I2S config
│   │   ├── esp32-cam.md                 # ESP32-CAM firmware, camera duty-cycling & touch
│   │   ├── pico-display.md              # RP2040 MicroPython ST7789 vector engine
│   │   └── pinout.md                    # Master unified wiring & pinout matrix
│   └── development/
│       └── development-guide.md         # Environment setup, simulation & debugging
│
├── software/                            # Production source code
│   ├── pi/                              # Raspberry Pi main orchestrator daemon
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── adam.service
│   │   └── src/
│   ├── esp32-cam/                       # ESP32-CAM Arduino C++ firmware
│   │   ├── README.md
│   │   └── src/
│   ├── pico/                            # Raspberry Pi Pico MicroPython face engine
│   │   ├── README.md
│   │   └── src/
│   └── laptop-agent/                    # Python companion host agent
│       ├── README.md
│       ├── requirements.txt
│       └── src/
│
├── apps/                                # Companion user applications
│   ├── README.md                        # Application suite documentation
│   ├── pc/                              # React 18 + Vite + Tailwind PC Dashboard
│   └── mobile/                          # Turborepo + Expo React Native Mobile App
│
├── assets/                              # Media, blueprints & brand assets
│   ├── images/                          # Schematics, high-res renders, photo diagrams
│   └── videos/                          # 3D animation renders and video demos
│
└── examples/                            # Testing utilities & developer recipes
    ├── README.md
    ├── mock_esp32_serial.py             # Hardware-free serial link simulator
    ├── custom_action_plugin.py          # Laptop Agent extension recipe
    └── test_audio_doa.py                # Standalone sound localization verification
```

---

## 🛠️ Hardware Bill of Materials (BOM)

| Component | Part / Model | Purpose | Voltage / Interface |
| :--- | :--- | :--- | :--- |
| **Main Processing Brain** | Raspberry Pi Zero 2 W (or Pi 4B) | Gemini Live client, DSP, orchestrator | 5V / 2.5A, Wi-Fi 802.11 b/g/n |
| **Vision & Touch Node** | ESP32-CAM (AI-Thinker) + OV2640 | Hardware JPEG camera, capacitive touch | 5V / 1A, UART2 (PL011) |
| **Digital Face Display** | Raspberry Pi Pico (RP2040) | MicroPython vector animation engine | 5V (VBUS) / 3.3V OUT, SPI 40MHz |
| **Display Panel** | 2.4" IPS TFT (ST7789 controller) | 320x240 RGB eye/mouth animation display | 3.3V, SPI bus |
| **Audio Input** | 2x INMP441 MEMS Microphones | Stereo audio capture & GCC-PHAT DOA | 3.3V, I2S bus (voiceHAT) |
| **Audio Output** | MAX98357A I2S Class-D DAC + 3W Speaker | High-clarity speech playback | 5V / 3.3V logic, I2S bus |
| **Actuators** | 2x SG90 / MG90S Micro Servos | Pan (yaw) and Tilt (pitch) head movement | 5V, 50Hz PWM |
| **Touch Sensors** | 4x TTP223 Capacitive Modules | Cheeks, forehead, chin physical inputs | 3.3V, Digital GPIO |
| **Power Distribution** | 5V 4A DC Step-Down / Buck Converter | Clean regulated power delivery | 7V-24V in -> 5.0V out |

For complete schematics and connection tables, refer to [**Master Pinout Reference**](docs/hardware/pinout.md).

---

## 🚀 Quick Start Guide

### 1. Flash Microcontroller Firmware

#### A. Raspberry Pi Pico (RP2040 Face Renderer)
1. Install [MicroPython](https://micropython.org/download/rp2-pico/) on your Pico.
2. Open Thonny or your preferred IDE and upload `software/pico/src/main.py` directly to the Pico as `main.py`.
3. Power cycle the Pico. You will see ADAM's digital eyes initialize and begin the default breathing/blinking cycle.

#### B. ESP32-CAM (Vision & Touch Node)
1. Open `software/esp32-cam/src/esp32_cam.ino` in the Arduino IDE.
2. Select Board: **AI Thinker ESP32-CAM**. Enable **PSRAM**.
3. Install the required `ESP32Servo` library.
4. Connect via an FTDI programmer and flash the sketch.

### 2. Configure the Raspberry Pi Zero 2 W

1. Install **Raspberry Pi OS (64-bit Lite, Debian 13 Trixie)** using Raspberry Pi Imager.
2. Enable SSH and connect to the Pi:
   ```bash
   ssh pi@adam-pi.local
   ```
3. Enable I2S and PL011 UART in `/boot/firmware/config.txt`:
   ```ini
   dtparam=i2s=on
   dtoverlay=googlevoicehat-soundcard
   enable_uart=1
   dtoverlay=disable-bt
   ```
4. Clone this repository onto the Pi:
   ```bash
   git clone https://github.com/dgentechnologies/ADAM-AI.git /home/pi/ADAM
   cd /home/pi/ADAM/software/pi
   ```
5. Install system and Python dependencies:
   ```bash
   sudo apt update && sudo apt install -y python3-venv portaudio19-dev libasound2-dev
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
6. Set your Google Gemini API key:
   ```bash
   cp ../../.env.example .env
   nano .env
   ```
7. Launch ADAM:
   ```bash
   python src/main.py
   ```

### 3. Production Deployment (systemd)

To make ADAM run automatically on system boot as a resilient background service:
```bash
sudo cp adam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adam.service
sudo systemctl start adam.service
sudo journalctl -u adam.service -f
```

---

## 💻 Companion Software & Apps

ADAM is fully equipped with companion client applications:
- **PC Dashboard (Vite / React / Tailwind)**: Desktop control interface to monitor ADAM's telemetry, conversation transcripts, and hardware status.
- **Mobile App (Expo / React Native)**: Mobile device companion for configuring Wi-Fi credentials, selecting voice models, and remote interaction.
- **Laptop Agent**: Python background service running on your workstation that allows ADAM to mute Spotify, adjust screen brightness, lock the workstation, or launch applications upon voice command.

Learn more in [**Companion Apps Guide**](apps/README.md).

---

## 🤝 Contributing

We warmly welcome contributions from the open-source community, robotics enthusiasts, and AI researchers! Please review our [**Contributing Guide**](CONTRIBUTING.md) to get started.

---

## ⚖️ License

ADAM AI is released under the **[Apache 2.0 License](LICENSE)**.  
Copyright &copy; 2026 **DGEN Technologies Pvt. Ltd.**

Commercial licensing, custom hardware integrations, and OEM deployments are available. For enterprise inquiries, contact **contact@dgentechnologies.com**.

---

## 🏢 Built by DGEN Technologies

**DGEN Technologies Pvt. Ltd.** — Kolkata, India  
*"Innovate. Integrate. Inspire." | Made with pride in India.*

- **Official Website**: [dgentechnologies.com](https://dgentechnologies.com)
- **Twitter / X**: [@dgen_tec](https://twitter.com/dgen_tec)
- **Instagram**: [@dgen_technologies](https://instagram.com/dgen_technologies)
- **LinkedIn**: [DGEN Technologies](https://linkedin.com/company/dgentechnologies)
