# Raspberry Pi Pico Face Display Engine

This directory contains the MicroPython vector graphics firmware for the **Raspberry Pi Pico (RP2040)**, which drives the 2.4" ST7789 IPS LCD.

---

## 🎨 Role & Graphics Pipeline

The Pico runs a dedicated 60 FPS rendering loop with zero runtime memory allocations:
1. **Pre-allocated Double Buffer**: Pre-allocates a 153.6 KB RGB565 frame buffer in SRAM at boot.
2. **Procedural Vector Engine**: Generates smooth procedural eye contours, dilated pupils, angled eyebrows, smiling/speaking mouth arcs, and blush cheeks.
3. **ST7789 Color Swapping**: Encodes colors with big-endian byte-swapping to match ST7789 SPI hardware requirements.
4. **Autonomous Animation**: Features randomized organic blinks and sinusoidal eye drift during idle states.
5. **Serial Command Listener**: Listens on UART0 RX (`GP1` @ 115,200 baud) for emotion strings relayed by the ESP32-CAM.

---

## 📂 Source Code Structure

```text
software/pico/
├── README.md               # Firmware architecture & flashing guide
└── src/
    └── main.py             # MicroPython vector face renderer
```

---

## 🚀 Installation & Flashing

1. Flash the standard **MicroPython UF2** firmware onto the Raspberry Pi Pico.
2. Connect the Pico to your computer via USB.
3. Open **Thonny IDE** and select **MicroPython (Raspberry Pi Pico)** in the bottom-right corner.
4. Open `software/pico/src/main.py` in Thonny.
5. Select **File -> Save As -> Raspberry Pi Pico** and save as **`main.py`**.
6. By default, `TESTING_MODE = True` is enabled in `main.py` for standalone testing without serial input.
   - For live operation with the robot, change line 33 to:
     ```python
     TESTING_MODE = False
     ```
7. Disconnect USB and wire the Pico into the robot according to the [Hardware Pinout Matrix](../../docs/hardware/pinout.md).
