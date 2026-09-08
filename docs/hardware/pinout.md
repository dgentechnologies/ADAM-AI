# ADAM Master Hardware Pinout Matrix

This document provides the authoritative, consolidated wiring cross-reference for all microprocessors, microcontrollers, and actuators in the ADAM system.

---

## 1. Raspberry Pi Zero 2 W Header Pinout (40-Pin GPIO)

<div align="center">
  <img src="../../assets/images/raspberry-pi-pinout-reference.webp" alt="Raspberry Pi Pinout Reference" width="550" />
</div>

| Physical Pin | Header Label | Function in ADAM | Connected Subsystem | Notes |
| :---: | :---: | :--- | :--- | :--- |
| **2** | **5V Power** | 5V Main Power Input | 5V Logic Rail (Buck Converter) | Stable regulated 5.0V |
| **4** | **5V Power** | 5V Supplemental Input | 5V Logic Rail | Paralleled with Pin 2 |
| **6** | **GND** | System Ground | Common Ground Rail | Star Ground Point |
| **8** | **GPIO 14 (TXD)** | UART2 Serial Transmit | **ESP32-CAM GPIO 16 (RX)** | PL011 UART @ 921,600 baud |
| **10** | **GPIO 15 (RXD)** | UART2 Serial Receive | **ESP32-CAM GPIO 4 (TX)** | PL011 UART @ 921,600 baud |
| **12** | **GPIO 18** | I2S BCLK (Bit Clock) | Google voiceHAT / INMP441 / MAX98357A | Audio serial clock |
| **32** | **GPIO 12 (PWM0)**| Pan Servo PWM Signal | **Pan Servo (MG90S)** Signal Pin | `gpiozero.AngularServo` (50Hz) |
| **35** | **GPIO 19** | I2S FS (Frame Sync / LRC) | Google voiceHAT / INMP441 / MAX98357A | Left/Right word clock |
| **38** | **GPIO 20** | I2S DIN (Data Input) | Google voiceHAT / INMP441 Mics | Stereo capture |
| **40** | **GPIO 21** | I2S DOUT (Data Output)| Google voiceHAT / MAX98357A Amp | Vocal playback |

---

## 2. ESP32-CAM (AI-Thinker) Pinout

| ESP32-CAM Pin | Connected Peripheral | Target Pin / Component | Electrical Spec |
| :--- | :--- | :--- | :--- |
| **5V** | Regulated Power | 5V Logic Rail | 5.0V @ 500mA peak |
| **GND** | Common Ground | Central Ground Rail | 0V Reference |
| **GPIO 4** | UART2 Transmit (TX) | **Raspberry Pi GPIO 15 (RXD, Pin 10)** | 3.3V CMOS @ 921,600 baud |
| **GPIO 16** | UART2 Receive (RX) | **Raspberry Pi GPIO 14 (TXD, Pin 8)** | 3.3V CMOS @ 921,600 baud |
| **GPIO 3 (U0RXD)**| UART1 Transmit (Relay)| **Raspberry Pi Pico GP1 (Pin 2)** | 3.3V CMOS @ 115,200 baud |
| **GPIO 13** | Tilt Servo Signal | **Tilt Servo (SG90)** Signal Pin | 50Hz PWM Output |
| **GPIO 12** | Touch Pad 1 Input | **Left Cheek** (TTP223 Output) | 3.3V Digital (Active HIGH) |
| **GPIO 14** | Touch Pad 2 Input | **Right Cheek** (TTP223 Output) | 3.3V Digital (Active HIGH) |
| **GPIO 15** | Touch Pad 3 Input | **Head / Stop** (TTP223 Output) | 3.3V Digital (Active HIGH) |
| **GPIO 2** | Touch Pad 4 Input | **Petting Pad** (TTP223 Output) | 3.3V Digital (Active HIGH) |

---

## 3. Raspberry Pi Pico (RP2040) Pinout

| Pico Pin | Physical Pin | Connected To | Interface | Purpose |
| :--- | :---: | :--- | :--- | :--- |
| **GP1** | **Pin 2** | **ESP32-CAM GPIO 3** | UART0 RX (115,200 baud) | Inbound emotion commands |
| **GP16** | **Pin 21** | **ST7789 DC** | Digital GPIO Output | Data / Command select |
| **GP17** | **Pin 22** | **ST7789 CS** | SPI0 Chip Select | Active LOW chip enable |
| **GP18** | **Pin 24** | **ST7789 SCLK** | SPI0 Clock (40 MHz) | High-speed display clock |
| **GP19** | **Pin 25** | **ST7789 MOSI** | SPI0 Master Out Slave In | Display pixel data stream |
| **GP20** | **Pin 26** | **ST7789 RST** | Digital GPIO Output | Hardware display reset |
| **3V3 OUT**| **Pin 36** | **ST7789 VCC & BL**| 3.3V Power Out | Display logic & LED backlight |
| **GND** | **Pin 38** | **ST7789 GND** | Common Ground | Ground reference |
| **VBUS** | **Pin 40** | **5V Logic Rail** | 5V Power In | Powers Pico onboard buck regulator |

---

## 4. Servo Actuators Pinout

Both servos are powered from the **Dedicated Actuator Rail** (isolated from microcomputer logic):

| Servo Function | Model | Power (VCC) | Ground (GND) | Signal (PWM) |
| :--- | :--- | :--- | :--- | :--- |
| **Pan Axis (Yaw)** | MG90S (Metal Gear) | 5V Actuator Rail | Common Ground | **Raspberry Pi GPIO 12 (Pin 32)** |
| **Tilt Axis (Pitch)**| SG90 (Micro Servo) | 5V Actuator Rail | Common Ground | **ESP32-CAM GPIO 13** |

---

## 5. Capacitive Touch Sensors (TTP223 Breakout)

| Touch Sensor | Location | Module VCC | Module GND | Module I/O Out |
| :--- | :--- | :--- | :--- | :--- |
| **Touch 1** | Left Cheek | 3.3V Rail | Common Ground | **ESP32-CAM GPIO 12** |
| **Touch 2** | Right Cheek | 3.3V Rail | Common Ground | **ESP32-CAM GPIO 14** |
| **Touch 3** | Head / Forehead | 3.3V Rail | Common Ground | **ESP32-CAM GPIO 15** |
| **Touch 4** | Chin / Petting | 3.3V Rail | Common Ground | **ESP32-CAM GPIO 2** |
