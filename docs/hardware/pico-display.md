# Raspberry Pi Pico Display & Vector Face Engine

ADAM's physical personality is brought to life by a dedicated **Raspberry Pi Pico (RP2040)** rendering high-frame-rate, expressive vector eyes and mouth animations on a 2.4" ST7789 IPS display.

---

## 1. Hardware Specifications & Wiring

```text
Raspberry Pi Pico (RP2040)                      2.4" ST7789 IPS LCD (320x240)
  GP19 (Physical Pin 25)  ────── SPI0 TX ──────▶ MOSI / SDA
  GP18 (Physical Pin 24)  ────── SPI0 SCK ─────▶ SCLK / SCL
  GP17 (Physical Pin 22)  ────── SPI0 CSn ─────▶ CS
  GP16 (Physical Pin 21)  ────── GPIO Out ─────▶ DC
  GP20 (Physical Pin 26)  ────── GPIO Out ─────▶ RESET / RST
  3V3 OUT (Pin 36)        ────── Power ────────▶ VCC & LED Backlight
  GND (Pin 38)            ────── Ground ───────▶ GND

ESP32-CAM (Relay Node)
  GPIO 3 (U0RXD Outbound) ────── UART0 RX ─────▶ GP1 (Physical Pin 2 on Pico)
  GND                     ────── Ground ───────▶ GND
```

> [!CAUTION]
> **Power Safety**: The ST7789 display logic must run on **3.3V**. Connecting the display VCC or logic lines to a 5V rail will permanently damage the ST7789 driver IC.

---

## 2. MicroPython Graphics Architecture

Rendering fluid animations on a resource-constrained microcontroller requires zero-heap runtime allocation to avoid triggering garbage collection pauses during animations.

### Static Frame Buffer Allocation
At boot, a single contiguous $153.6\text{ KB}$ buffer is pre-allocated:
```python
W, H = 320, 240
# 320 * 240 * 2 bytes = 153,600 bytes
_buf = bytearray(W * H * 2)
fb = framebuf.FrameBuffer(_buf, W, H, framebuf.RGB565)
```

### ST7789 RGB565 Byte-Swapping
The ST7789 SPI controller interprets color words as big-endian. Standard MicroPython `framebuf` colors must be byte-swapped before writing:
```python
def _c(r, g, b):
    # Standard 16-bit RGB565 encoding
    v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    # Swap high and low bytes for ST7789 SPI bus
    return ((v & 0xFF) << 8) | (v >> 8)

WHITE  = _c(255, 255, 255)
BG     = _c(  0,   0,   0)
BLUE   = _c( 70, 130, 255)
PINK   = _c(255,  90, 110)
YELLOW = _c(255, 230,  60)
```

---

## 3. Supported Emotion State Machine

The Pico listens on `GP1` (UART0 RX @ 115,200 baud) for plain newline-terminated ASCII tokens:

| Emotion Command | Visual Expression | Color Tone |
| :--- | :--- | :--- |
| `idle` | Gentle sinusoidal vertical eye float with randomized organic blinks. | Cyan / White |
| `speaking` | Eyes narrow slightly; mouth opens/closes with simulated speech syllables. | White / Cyan |
| `happy` | Cheerful inverted-U arched eyes, wide curved smile, and blush cheek spots. | Warm Pink / White |
| `sad` | Slanted downturned brows, drooped pupils, and frowning mouth arc. | Deep Blue |
| `angry` | Sharply angled wedge eyebrows, compressed vertical slit pupils, flat mouth. | Crimson Red |
| `panic` | Rapid horizontal saccades with erratic pupil dilation and vibrating mouth. | Vibrant Amber |
| `surprised` | Massive circular dilated pupils, raised arches, round O-shaped mouth. | Pale Yellow |
| `shy` | Eyes avert downward-right, soft blinks, rosy pink blush cheeks. | Sakura Pink |
| `sleep` | Eyelids close to horizontal slit lines with rhythmic expansion/contraction. | Dim Blue-Grey |
| `thinking` | Pupils drift to top-right corner; oscillating dots render beneath. | Electric Indigo |
| `reconnecting`| Concentric spinning radar arcs symbolizing active network handshake. | Amber Gold |
| `love` | Eyes morph into pulsing heart vectors. | Magenta |
| `confused` | One brow raised high, one brow lowered; pupils asymmetrical. | Mint Green |
| `rizz` | Left eye winks closed with playful tilt; confident smirk mouth. | Warm Gold |

---

## 4. Setup & Deployment Guide

1. Download the latest **MicroPython UF2 firmware for Raspberry Pi Pico** from [micropython.org](https://micropython.org/download/rp2-pico/).
2. Hold down the **BOOTSEL** button on the Pico while plugging the USB cable into your workstation.
3. Drag and drop the `.uf2` file onto the mounted `RPI-RP2` drive. The Pico will reboot into MicroPython.
4. Launch **Thonny IDE** and set the interpreter to **MicroPython (Raspberry Pi Pico)**.
5. Open `software/pico/src/main.py`.
6. Save the file directly onto the microcontroller as **`main.py`** (this ensures the code launches automatically whenever power is applied).
7. Reset or power-cycle the Pico.
