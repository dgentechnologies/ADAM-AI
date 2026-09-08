# ESP32-CAM Hardware & Firmware Guide (v40)

The **AI-Thinker ESP32-CAM** module serves as ADAM's peripheral co-processor, responsible for high-resolution optical capture, capacitive touch sensing, tilt servo actuation, and emotion command relaying.

---

## 1. Pin Map & Hardware Connections

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

### Communication & Peripheral Pinout Table

| ESP32-CAM Pin | Connected Peripheral | Target Board / Pin | Mode / Protocol | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **5V** | 5V Logic Rail | Regulated 5V Buck Converter | Power (5.0V @ 500mA peak) | Module power |
| **GND** | Star Ground | Common Ground Rail | 0V Reference | Ground |
| **GPIO 4** | UART2 TX | **Raspberry Pi GPIO 15 (RXD, Pin 10)** | 921,600 baud (8N1) | Frames, touch & gesture events |
| **GPIO 16** | UART2 RX | **Raspberry Pi GPIO 14 (TXD, Pin 8)** | 921,600 baud (8N1) | Control commands (`CAM:`, `TILT:`, `EMO:`) |
| **GPIO 3 (U0RXD)**| UART1 TX (Relay) | **Raspberry Pi Pico GP1 (Pin 2)** | 115,200 baud (8N1) | One-way emotion string relay |
| **GPIO 13** | Tilt Servo Signal | **Tilt Servo (SG90)** Signal Pin | 50Hz PWM Output | Head pitch angle (45° - 135°) |
| **GPIO 12** | Touch 1 Input | **Left Cheek** (TTP223 Output) | Digital Input | Cheek tap / petting sensor |
| **GPIO 14** | Touch 2 Input | **Right Cheek** (TTP223 Output) | Digital Input | Cheek tap / petting sensor |
| **GPIO 15** | Touch 3 Input | **Head / Stop** (TTP223 Output) | Digital Input | Stop / attention wake sensor |
| **GPIO 2** | Touch 4 Input | **Chin / Petting** (TTP223 Output) | Digital Input | Petting gesture sensor |

> [!WARNING]
> **GPIO 3 Flashing Contention Warning**:  
> `GPIO 3` is the physical hardware programming RX pin (U0RXD). ADAM's firmware dynamically reconfigures this pin as `UART1 TX` to relay emotion strings to the Pico. Whenever you connect an FTDI adapter to reflash the ESP32-CAM, **physically disconnect the wire between ESP32 GPIO 3 and Pico GP1** to prevent electrical bus contention during flashing.

---

## 2. Capacitive Touch Matrix: TTP223 Module Configuration

ADAM uses four **TTP223 capacitive touch sensor modules**. Improper solder jumper configuration on these modules is the #1 cause of "stuck touches" where the robot registers a touch permanently:

### Solder Jumper Configuration
Look at the solder bridge pads on the rear of the TTP223 PCB:
- **Jumper A (Latch / Toggle Mode)**:
  - **MUST BE OPEN (Default / Required)**: Sets **Momentary Mode**. Output is HIGH only while your finger is physically on the pad; drops immediately to LOW when released.
  - **DO NOT BRIDGE**: Bridging Jumper A sets **Toggle Mode**, where one tap locks the output HIGH permanently until tapped a second time.
- **Jumper B (Output Polarity)**:
  - **OPEN**: Active HIGH (Pin reads 3.3V when touched, 0V when idle). Firmware defaults to active-HIGH (`TOUCHx_ACTIVE_LOW 0`).
  - **BRIDGED**: Active LOW.

### JTAG Strapping Pin Noise & Firmware Filtering
`GPIO 14` and `GPIO 15` are ESP32 JTAG strapping pins and sit adjacent to the camera sensor's high-speed clock traces (XCLK/PCLK). To eliminate electrical phantom touches:
1. **Three-Sample Majority Voting**: The firmware samples each pin 3 times consecutively per 20ms poll cycle and takes the majority vote.
2. **State-Change Debounce**: A pin must read consistently active for `TOUCH_DEBOUNCE_MS = 60` milliseconds straight before a touch packet (`T<n>:1\n`) is dispatched to the Pi.

---

## 3. Camera Duty-Cycling & Thermal Management

Continuous video clocking through the OV2640 sensor causes internal chip temperatures to exceed 70°C, inducing thermal noise in images. The firmware implements dynamic duty-cycling:

```cpp
void handleSerialCommands() {
    if (cmd == "CAM:ON") {
        esp_camera_init(&camera_config);  // Power up sensor & DMA clock
        camera_active = true;
    } else if (cmd == "CAM:OFF") {
        esp_camera_deinit();              // Cut sensor clock to 0 mA
        camera_active = false;
    }
}
```

---

## 4. Arduino IDE Flashing Guide

### Required Libraries & Board Package
- Board Package: **esp32 by Espressif Systems** (v2.0.14 or later).
- Library: **ESP32Servo** by Kevin Harrington (available via Arduino Library Manager).

### Arduino IDE Board Settings
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
   - FTDI `TX`  -> ESP32-CAM `U0RXD (GPIO 3)`
   - FTDI `RX`  -> ESP32-CAM `U0TXD (GPIO 1)`
2. **Jumper GPIO 0 to GND** (enters bootloader mode).
3. Connect FTDI to PC, select the COM port in Arduino IDE, and click **Upload**.
4. When upload finishes ("Leaving... Hard resetting via RTS pin..."):
   - **Disconnect GPIO 0 from GND**.
   - Press the on-board **RESET** button.
5. Disconnect the FTDI programmer and reconnect `GPIO 3` to the Raspberry Pi Pico `GP1` pin.
