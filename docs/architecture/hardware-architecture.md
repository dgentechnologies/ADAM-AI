# ADAM Hardware & Electrical Architecture (v40)

This document provides electrical engineering specifications, power distribution guidelines, thermal mitigation strategies, and critical hardware fault remedies based on measured data from physical ADAM prototypes.

---

## 1. Power Distribution Network (PDN) & Brownout Prevention

ADAM integrates microcomputers, microcontrollers, high-power I2S Class-D amplifiers, and inductive servo motors on a shared DC supply. Brownouts (where inductive motor spikes or amplifier transients drop the 5V rail below the Raspberry Pi's 4.63V Under-Voltage Lockout threshold) are prevented via a strict **star-topology architecture**:

```text
[DC Input: 7V - 24V (e.g. 12V 3A DC Jack) or USB-C PD (30W)]
                           │
                           ▼
     [High-Efficiency Synchronous Buck Converter]
               (5.0V @ 5.0A Continuous)
                           │
      ┌────────────────────┴─────────────────────┐
      │ (Clean Logic Rail 5.0V)                  │ (Noisy Actuator Rail 5.0V)
      │                                          │
      ├─▶ Pi Zero 2 W (Header Pins 2 & 4)        ├─▶ Pan Servo (MG90S) VCC
      ├─▶ ESP32-CAM (5V Pin)                     ├─▶ Tilt Servo (SG90) VCC
      ├─▶ RP2040 Pico (VBUS Pin 40)              │
      ├─▶ MAX98357A I2S Amplifier VCC            └─▶ [Bulk 1000µF Low-ESR Capacitor]
      │
      └─▶ [0.1µF Ceramic High-Freq Decoupling]
                           │
                           ▼
                  [Common Star Ground Point]
```

### Prototype Measured Current Draws

| Subsystem | Rail | Operating Voltage | Idle Current | Peak Current | Electrical Phenomenon |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Raspberry Pi Zero 2 W** | Logic | 5.0V | 260 mA | 1,200 mA | BCM2710A1 4-core DSP burst + 2.4GHz Wi-Fi |
| **ESP32-CAM AI-Thinker** | Logic | 5.0V (Internal LDO)| 110 mA | 420 mA | OV2640 clocking + hardware JPEG compression |
| **Pico RP2040 + ST7789** | Logic | 5.0V (VBUS) | 75 mA | 130 mA | 40MHz SPI bus clocking + LCD LED backlight |
| **MAX98357A + 3W Speaker**| Logic | 5.0V | 25 mA | 850 mA | Peak volume vocal bursts |
| **Pan Servo (MG90S)** | Actuator | 5.0V | 15 mA (Detached) | 950 mA | Fast acceleration / direction reversal stall |
| **Tilt Servo (SG90)** | Actuator | 5.0V | 12 mA (Holding) | 700 mA | Mechanical pitch hold torque |
| **Total System Demand** | **—** | **5.0V** | **~497 mA** | **~4,250 mA** | **All subsystems firing concurrently** |

---

## 2. Documented Hardware Faults & Physical Fixes

The following critical hardware issues were isolated and documented during hardware prototyping:

### Fault B1: MAX98357A Floating `GAIN` Pin (Volume Drift)
- **Symptom**: Voice output volume randomly jumps up and down between utterances with no software configuration changes.
- **Root Cause**: On the MAX98357A I2S DAC breakout board, the `GAIN` pin controls the internal amplifier gain (options: 3dB, 6dB, 9dB, 12dB, 15dB). If left floating, internal parasitic capacitance drifts, causing continuous gain fluctuations.
- **Hardware Fix**: Solder a pull-down resistor from `GAIN` to `GND` (sets fixed 9dB gain) or connect directly to `GND` (sets fixed 12dB gain). Never leave the `GAIN` pin floating.

### Fault B5: Power Rail Sag & Missing Bulk Decoupling
- **Symptom**: Speaker crackles or emits static clicks whenever speech begins or servos move.
- **Hardware Fix**: Place a $1000\mu\text{F}$ 16V low-ESR electrolytic capacitor across the 5V actuator rail directly next to the servo headers. Place a $100\mu\text{F}$ capacitor adjacent to the MAX98357A VCC pin.

### Fault A11: Right Microphone Dead Channel on Vero Board
- **Symptom**: ADAM frequently mishears consonants (e.g. "Hello ADAM" $\rightarrow$ "Hello madam"), and direction-of-arrival (DOA) acoustic tracking fails.
- **Root Cause**: On hand-soldered Vero/perf-board prototypes, if the right INMP441 microphone's `SD` (serial data) line is floating or `WS`/`LRCL` has an intermittent cold joint, the channel emits continuous white hiss (measured at $-24.8\text{ dBFS}$, $11.4\text{ dB}$ louder than the live left mic). When software averages left and right channels (`mix` mode), the hiss destroys high-frequency consonant cues (2 kHz – 8 kHz).
- **Physical Verification**:
  1. Inspect continuity between the right mic's `SD` pin and Pi GPIO 20 (DIN).
  2. Inspect continuity of `WS` / `LRCL` to Pi GPIO 19.
  3. Verify that the Left mic has its `L/R` pin tied to `GND` (selects Left slot) and the Right mic has `L/R` tied to `3.3V` (selects Right slot).
- **Software Failsafe**: `audio_utils.py` contains `_MicChannelLiveness`, which automatically detects this fault, drops the right mic, and latches to `left` mode to recover 11.7 dB to 21 dB of intelligibility.

### Fault: Servo Mechanical Hum Acoustic Coupling
- **Symptom**: Microphones read continuous high background RMS ($>4500$), pinning the VAD gate open and causing Gemini to transcribe phantom speech in random languages.
- **Root Cause**: Standard 50Hz servo PWM pulses keep motor coils continuously energized. Mechanical motor hum conducts structurally through the 3D-printed chassis directly into the microphone diaphragms.
- **Software Mitigation**: `hardware.py` executes an auto-detach routine: the servo is energized for `NECK_SERVO_HOLD_S = 0.6s` to execute the gesture, then PWM is detached. The gearbox holds position on mechanical friction, returning the room noise floor to baseline (~1100 RMS).

### TTP223 Capacitive Touch Jumper Configuration
- **Symptom**: Touching the robot's cheek once causes the touch state to lock permanently ON until touched again.
- **Root Cause**: TTP223 modules feature solder pads **A** and **B**. Jumper A defaults to Toggle/Latch mode on some manufacturer batches.
- **Required Hardware State**:
  - **Jumper A MUST BE OPEN**: Configures momentary output (HIGH only while touched, immediately LOW when released).
  - **Jumper B OPEN**: Configures active-HIGH output logic (3.3V when touched).

---

## 3. Signal Integrity & Level Compatibility

All core logic lines (Raspberry Pi Zero 2 W, ESP32-CAM, Raspberry Pi Pico) operate natively at **3.3V CMOS**:

```text
Raspberry Pi Zero 2 W (3.3V) <────── UART2 (921,600 baud) ──────> ESP32-CAM (3.3V)
  GPIO 14 (TXD, Pin 8)  ────────────────────────────────────────▶ GPIO 16 (RX)
  GPIO 15 (RXD, Pin 10) ◀──────────────────────────────────────── GPIO 4  (TX)
  GND (Pin 6)           ══════════════════════════════════════════ GND

ESP32-CAM (3.3V)             <────── UART1 (115,200 baud) ──────> RP2040 Pico (3.3V)
  GPIO 3 (U0RXD / Outbound)  ────────────────────────────────────▶ GP1 (UART0 RX, Pin 2)
  GND                        ══════════════════════════════════════ GND
```

> [!CAUTION]
> **ESP32-CAM Flashing Bus Contention**:  
> `GPIO 3` on the ESP32-CAM is the physical hardware UART0 RX pin used by the USB-serial programmer (FTDI) during flashing. In ADAM's firmware, `GPIO 3` is dynamically remapped to act as the outbound `UART1 TX` relay to the Pico. Whenever you connect an FTDI programmer to reflash the ESP32-CAM, **physically disconnect the jumper wire between ESP32 GPIO 3 and Pico GP1** to prevent electrical contention on the flashing bus.

---

## 4. Acoustic Enclosure Isolation

1. **Sealed Speaker Enclosure**: The 3W speaker must be sealed within its own airtight acoustic chamber using silicone sealant or a closed-cell foam gasket. An unsealed speaker will pressurize the interior of the robot's head, driving the microphone diaphragms internally and causing immediate acoustic feedback and gate latching.
2. **Servo Vibration Isolation**: Mount the pan servo using silicone vibration-dampening rubber eyelets. Rigid plastic-to-plastic screw mountings conduct motor gearbox vibrations directly to the chassis frame.
3. **Microphone Placement**: The two INMP441 microphones must be mounted flush with the exterior shell with acoustic port holes ($2\text{ mm}$ diameter) facing outward, isolated from interior chassis cavities.
