# ADAM Hardware & Electrical Architecture

This document provides engineering specifications for ADAM's power distribution, thermal mitigation, signal integrity, and mechanical integration.

---

## 1. Electrical Power Distribution Network (PDN)

Robotics projects combining microcomputers, wireless radios, audio amplifiers, and inductive servo motors often fail due to electrical brownouts. ADAM addresses this with a disciplined **star-topology power distribution network**:

```text
[DC Power In (7V - 24V) or USB-C PD (15W+)]
                    │
                    ▼
   [High-Efficiency Synchronous Buck Converter]
              (5.0V @ 5.0A Continuous)
                    │
      ┌─────────────┴──────────────┐
      │ (Clean Logic Rail 5.0V)    │ (Noisy Actuator Rail 5.0V)
      │                            │
      ├─▶ Pi Zero 2 W (5V Pin 2,4) ├─▶ Pan Servo VCC (SG90/MG90S)
      │                            ├─▶ Tilt Servo VCC (SG90/MG90S)
      ├─▶ ESP32-CAM (5V Pin)       │
      │                            └─▶ [Bulk 1000µF Low-ESR Decoupling Cap]
      ├─▶ MAX98357A I2S Amplifier
      │
      └─▶ RP2040 Pico (VBUS Pin 40)
```

### Power Budget & Current Draw Analysis

| Subsystem | Operating Voltage | Nominal Current | Peak Current | Critical Conditions |
| :--- | :--- | :--- | :--- | :--- |
| **Raspberry Pi Zero 2 W** | 5.0V | 280 mA | 1,200 mA | Heavy DSP cross-correlation + Wi-Fi burst |
| **ESP32-CAM Node** | 5.0V (Internal LDO) | 120 mA | 450 mA | Camera DMA transfer + sensor clocking |
| **RP2040 Pico + ST7789 TFT**| 5.0V (VBUS -> 3.3V) | 70 mA | 120 mA | 40MHz SPI transfer + 100% TFT backlight |
| **MAX98357A + 3W Speaker** | 5.0V | 80 mA | 850 mA | Maximum volume vocal response |
| **Pan Servo (MG90S)** | 5.0V (Actuator rail) | 150 mA | 900 mA | Fast acceleration / directional reversal |
| **Tilt Servo (SG90)** | 5.0V (Actuator rail) | 100 mA | 750 mA | Elevation tilt holding torque |
| **Total System Draw** | **5.0V** | **~800 mA** | **~4,270 mA** | **All subsystems firing simultaneously** |

### Brownout Prevention Rules
1. **Separated Rails**: Never draw servo motor power directly from the Raspberry Pi 5V header pins. Sudden motor stall currents create inductive spikes and voltage drops below 4.63V, triggering the Pi's Under-Voltage Lockout (UVLO).
2. **Decoupling Capacitors**: Place a minimum $1000\mu\text{F}$ 16V low-ESR electrolytic capacitor across the servo 5V rail as close to the servo connectors as possible. Place a $0.1\mu\text{F}$ ceramic capacitor across logic power inputs to filter high-frequency switching noise.
3. **Common Ground**: All grounds (Pi GND, ESP32 GND, Pico GND, Servo GND, Power Supply GND) must unite at a central star ground point to eliminate ground loops that corrupt high-speed UART and I2S lines.

---

## 2. Logic Level Compatibility & Signal Integrity

All three processing cores operate with **3.3V CMOS logic**, enabling direct interconnects without level shifters when properly wired:

```text
Raspberry Pi Zero 2 W (3.3V) <====== 921,600 baud UART ======> ESP32-CAM (3.3V)
  GPIO14 (TXD) ──────────────────────────────────────────────▶ GPIO16 (RX)
  GPIO15 (RXD) ◀────────────────────────────────────────────── GPIO4  (TX)
  GND          ══════════════════════════════════════════════ GND

ESP32-CAM (3.3V)             <====== 115,200 baud UART ======> Raspberry Pi Pico (3.3V)
  GPIO3 (U0RXD / Outbound)   ────────────────────────────────▶ GP1 (UART0 RX)
  GND                        ══════════════════════════════════ GND
```

> [!WARNING]
> **Reflashing Notice for ESP32-CAM GPIO3**:  
> GPIO3 is the hardware flashing RX pin on the ESP32-CAM module. While running ADAM, GPIO3 is dynamically reconfigured as the software UART1 TX line to the Pico. Whenever you connect an FTDI programmer to reflash the ESP32-CAM via USB-serial, **temporarily disconnect the jumper from GPIO3 to the Pico** to prevent bus contention during programming.

---

## 3. Thermal Management

Enclosing high-performance computing hardware inside a compact robotic head creates thermal challenges:
1. **Raspberry Pi Zero 2 W**: The BCM2710A1 quad-core SoC produces significant heat under continuous audio DSP and network streaming. 
   - *Mitigation*: Mount a miniature aluminum heatsink ($14\times 14\times 6\text{ mm}$) to the SoC. Ensure the 3D-printed chassis features passive convection vents along the base and top crown.
2. **ESP32-CAM Sensor**: The OV2640 sensor core heats up during active video clocking, degrading image quality with thermal noise.
   - *Mitigation*: The firmware implements **duty-cycling**. Unless visual analysis is actively triggered, the sensor clock is disabled (`esp_camera_deinit()`), maintaining idle temperatures near ambient.

---

## 4. Mechanical & Acoustic Isolation

```text
       ┌────────────────────────┐
       │   Upper Head Shell     │
       │  (ST7789 TFT + Pico)   │
       └───────────┬────────────┘
                   │ Tilt Axis (SG90 Servo - Pitch)
       ┌───────────┴────────────┐
       │      Neck Bracket      │
       └───────────┬────────────┘
                   │ Pan Axis (MG90S Servo - Yaw)
       ┌───────────┴────────────┐
       │       Base Body        │
       │ (Pi Zero, Amp, Speaker)│
       └────────────────────────┘
```

### Acoustic Isolation for Microphone Arrays
For sound localization (DOA) and voice recognition to succeed while speaking or moving:
- **Speaker Isolation**: The 3W speaker chamber must be sealed from the interior of the head with silicone gaskets. Unsealed speaker pressure waves will travel through the enclosure and directly overdrive the INMP441 microphone diaphragms.
- **Motor Vibration Dampening**: Mount servos using silicone rubber grommets. Structural vibrations from motor gearboxes register as low-frequency rumble in the microphone capture pipeline.
- **Microphone Porting**: Keep acoustic port holes for the two INMP441 microphones equidistant from the chassis centerline and facing outward.
