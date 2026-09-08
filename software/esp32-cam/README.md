# ESP32-CAM Peripheral & Vision Firmware

This directory contains the production Arduino C++ firmware for the **AI-Thinker ESP32-CAM** peripheral node.

---

## 🎯 Role & Capabilities

1. **JPEG Camera Streaming**: Captures frames from the OV2640 image sensor and streams them via high-speed UART (`UART2` @ 921,600 baud) to the Raspberry Pi.
2. **Dynamic Camera Duty-Cycling**: Listens for `CAM:ON` and `CAM:OFF` commands to initialize/de-initialize the camera peripheral, preventing sensor overheating.
3. **Capacitive Touch Matrix**: Reads four TTP223 capacitive sensors (left cheek, right cheek, head, chin), applies 3-sample majority voting and a 60ms debounce filter, and forwards state change events to the Pi.
4. **Tilt Servo Actuation**: Controls the head tilt servo on GPIO13 based on inbound `TILT:<degrees>` serial commands.
5. **Dual-UART Emotion Relay**: Receives inbound `EMO:<name>` commands from the Pi on `UART2`, strips the prefix, and forwards the bare token `<name>\n` via `UART1` (GPIO3 TX @ 115,200 baud) directly to the Raspberry Pi Pico face display.

---

## 📂 Source Code Structure

```text
software/esp32-cam/
├── README.md               # Firmware reference and flashing instructions
└── src/
    └── esp32_cam.ino       # Complete unified Arduino firmware
```

---

## ⚡ Flashing Instructions

### Prerequisites
- **Arduino IDE** (v2.x recommended) or **Arduino CLI**.
- **ESP32 Board Package**: Install `esp32` by Espressif Systems (v2.0.14+).
- **Library Dependency**: `ESP32Servo` by Kevin Harrington.

### Hardware Connection (FTDI to ESP32-CAM)
```text
FTDI 5V   ──▶ ESP32-CAM 5V
FTDI GND  ──▶ ESP32-CAM GND
FTDI TX   ──▶ ESP32-CAM U0RXD (GPIO 3)
FTDI RX   ──▶ ESP32-CAM U0TXD (GPIO 1)
```

> [!IMPORTANT]
> **Bootloader Mode**: Connect a jumper wire between **GPIO 0 and GND** before powering on the board or pressing the RESET button. When flashing completes, disconnect GPIO 0 from GND and press RESET.

### Board Settings
- **Board**: `AI Thinker ESP32-CAM`
- **CPU Frequency**: `240MHz`
- **Flash Frequency**: `80MHz`
- **Partition Scheme**: `Huge APP (3MB No OTA/1MB SPIFFS)`
- **PSRAM**: `Enabled`
- **Upload Speed**: `921600`
