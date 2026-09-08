# ESP32-CAM Hardware & Firmware Guide

The **ESP32-CAM (AI-Thinker)** module serves as ADAM's peripheral controller, managing high-resolution optical capture, capacitive touch sensing, tilt servo actuation, and emotion command relaying.

---

## 1. Hardware Architecture & Pin Map

```text
                     ┌───────────────────────────┐
                     │    ESP32-CAM AI-Thinker   │
                     │  (Dual-Core LX6, 4MB PSRAM)
                     └──────┬─────────────┬──────┘
                            │             │
              OV2640 Camera │             │ Tilt Servo (50Hz PWM)
            (Direct DVP Bus)│             │
                            │             ▼ GPIO 13
                            │       [Tilt Servo SG90]
                            ▼
     ┌─────────────────────────────────────────────────┐
     │ Capacitive Touch Sensor Matrix (TTP223 Modules) │
     │  • Touch 1 (Left Cheek)  ──▶ GPIO 12            │
     │  • Touch 2 (Right Cheek) ──▶ GPIO 14            │
     │  • Touch 3 (Head / Stop) ──▶ GPIO 15            │
     │  • Touch 4 (Petting Pad) ──▶ GPIO 2             │
     └─────────────────────────────────────────────────┘
```

### Communication Pinout

| Peripheral | ESP32-CAM Pin | Connected To | Baud Rate / Mode | Function |
| :--- | :--- | :--- | :--- | :--- |
| **UART2 TX** | **GPIO 4** | Pi GPIO 15 (Pin 10) | 921,600 baud | JPEG frames, touch & gesture events |
| **UART2 RX** | **GPIO 16** | Pi GPIO 14 (Pin 8) | 921,600 baud | Control commands: `CAM:`, `TILT:`, `EMO:` |
| **UART1 TX** | **GPIO 3** | Pico GP1 (Pin 2) | 115,200 baud | One-way emotion string relay to Pico |
| **Tilt Servo**| **GPIO 13** | Signal (Yellow/Orange)| 50 Hz PWM | Vertical pitch adjustment (45° - 135°) |
| **Power** | **5V / GND** | Regulated 5V Rail | 5.0V @ 1A | Core power input |

---

## 2. Capacitive Touch Sensing: TTP223 Configuration

ADAM uses four **TTP223 capacitive touch breakout boards**. Improper module jumper configuration is the #1 cause of "stuck touches":

### Crucial Hardware Solder Jumpers:
The TTP223 module features two small solder bridge pads on the back, labeled **A** and **B**:
- **Jumper A (Latch / Toggle Mode)**:
  - **OPEN (Default / Recommended)**: **Momentary Mode**. Output is HIGH only while your finger is touching the pad; immediately returns LOW when released.
  - **BRIDGED**: **Toggle Mode**. Touching once sets the output HIGH, and it *stays HIGH permanently* until touched a second time. **Ensure Jumper A is OPEN.**
- **Jumper B (Output Polarity)**:
  - **OPEN**: Active HIGH (Pin reads 3.3V when touched, 0V when idle).
  - **BRIDGED**: Active LOW (Pin reads 0V when touched, 3.3V when idle).

### JTAG Pin Strapping & Firmware Debounce
`GPIO 14` and `GPIO 15` double as ESP32 JTAG strapping pins and run physically adjacent to high-speed camera clock lines (XCLK/PCLK). To eliminate electrical phantom touches, the firmware implements:
1. **Three-Sample Majority Voting**: Each 20ms poll cycle samples the pin 3 times; a state change requires at least 2 matching samples.
2. **State Debounce Threshold**: The pin must maintain a consistent HIGH state for 60ms continuously (`TOUCH_DEBOUNCE_MS = 60`) before a touch event packet (`T<n>:1\n`) is dispatched to the Pi.

---

## 3. Camera Duty-Cycling & Thermal Protection

Continuous active frame streaming through the OV2640 sensor causes internal silicon die temperatures to exceed 70°C, increasing chromatic sensor noise and risking long-term degradation.

The firmware implements dynamic camera duty-cycling:
```cpp
void handleSerialCommands() {
    if (cmd == "CAM:ON") {
        esp_camera_init(&camera_config);  // Power up clock & sensor
        camera_active = true;
    } else if (cmd == "CAM:OFF") {
        esp_camera_deinit();              // Cut sensor clock to 0 mA
        camera_active = false;
    }
}
```

---

## 4. Arduino IDE Flashing Guide

### Required Libraries
- `ESP32Servo` by Kevin Harrington (Install via Arduino Library Manager)
- `esp32` board package by Espressif (v2.0.14+ recommended)

### Board Settings in Arduino IDE
```text
Board:                  "AI Thinker ESP32-CAM"
CPU Frequency:          "240MHz (WiFi/BT)"
Flash Frequency:        "80MHz"
Flash Mode:             "QIO"
Partition Scheme:       "Huge APP (3MB No OTA/1MB SPIFFS)"
Core Debug Level:       "None"
PSRAM:                  "Enabled"
Upload Speed:           "921600" (or 115200 if using budget FTDI cables)
```

### Flashing Procedure
1. Connect FTDI Programmer to ESP32-CAM:
   - FTDI `5V`  -> ESP32-CAM `5V`
   - FTDI `GND` -> ESP32-CAM `GND`
   - FTDI `TX`  -> ESP32-CAM `U0RXD (GPIO3)`
   - FTDI `RX`  -> ESP32-CAM `U0TXD (GPIO1)`
2. **Jumper GPIO 0 to GND** (enters bootloader mode).
3. Connect FTDI to PC, select the COM port in Arduino IDE, and click **Upload**.
4. When upload completes, **disconnect GPIO 0 from GND** and press the on-board **RESET** button.
5. Disconnect FTDI and reconnect `GPIO 3` to the Raspberry Pi Pico GP1 RX pin.
