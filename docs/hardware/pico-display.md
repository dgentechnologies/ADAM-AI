# Raspberry Pi Pico Display & Vector Face Engine (v40)

ADAM's physical facial expressions are driven by a dedicated **Raspberry Pi Pico (RP2040)** running a custom MicroPython procedural vector graphics engine on a 2.4" ST7789 IPS LCD (320x240 pixels).

---

## 1. Hardware Pinout & Wiring

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
> **Voltage Constraint**: The ST7789 display controller and Pico RP2040 GPIOs operate on **3.3V**. Connecting the display VCC or logic lines to a 5V rail will permanently damage the display.

---

## 2. MicroPython Vector Engine Architecture

To maintain a consistent 60 FPS without memory fragmentation or garbage collection pauses on the RP2040:

### A. Static Pre-Allocated Frame Buffer
The engine allocates a single contiguous $153.6\text{ KB}$ buffer once at boot:
```python
W, H = 320, 240
# Pre-allocate 153.6 KB RGB565 framebuffer in SRAM
_buf = bytearray(W * H * 2)
fb = framebuf.FrameBuffer(_buf, W, H, framebuf.RGB565)
```

### B. Hardware Big-Endian Color Swapping
The ST7789 display controller expects big-endian 16-bit color words over SPI. Standard MicroPython `framebuf` colors must have their high and low bytes swapped:
```python
def _c(r, g, b):
    # Standard 16-bit RGB565 encoding: 5 bits red, 6 bits green, 5 bits blue
    v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    # Byte-swap for ST7789 SPI bus
    return ((v & 0xFF) << 8) | (v >> 8)

BG      = _c(  0,   0,   0)
WHITE   = _c(255, 255, 255)
PINK    = _c(255,  90, 110)
BLUE    = _c( 70, 130, 255)
YELLOW  = _c(255, 230,  60)
```

---

## 3. Supported Emotion States

The Pico listens on `GP1` (UART0 RX @ 115,200 baud) for plain newline-terminated ASCII tokens:

| Emotion Command | Visual Expression | Color Tone |
| :--- | :--- | :--- |
| `idle` | Gentle sinusoidal vertical eye float with randomized organic blinks. | Cyan / White |
| `speaking` | Eyes narrow slightly; mouth opens and closes in rhythm with speech. | White / Cyan |
| `happy` | Inverted-U arched eyes, wide curved smile, and blush cheek spots. | Warm Pink / White |
| `sad` | Slanted downturned brows, drooped pupils, and curved frown. | Deep Blue |
| `angry` | Sharply angled wedge eyebrows, compressed vertical pupils, flat mouth. | Crimson Red |
| `panic` | Rapid horizontal saccades with erratic pupil dilation and vibrating mouth. | Vibrant Amber |
| `surprised` | Massive circular dilated pupils, raised arches, round O-shaped mouth. | Pale Yellow |
| `shy` | Eyes avert downward-right, soft blinks, rosy pink blush cheeks. | Sakura Pink |
| `sleep` | Eyelids close to horizontal slit lines with rhythmic expansion. | Dim Blue-Grey |
| `thinking` | Pupils drift to top-right corner; oscillating indicator dots beneath. | Electric Indigo |
| `reconnecting`| Concentric spinning radar arcs symbolizing active network handshake. | Amber Gold |
| `love` | Eyes morph into pulsing heart vectors. | Magenta |
| `confused` | One brow raised high, one brow lowered; pupils asymmetrical. | Mint Green |
| `rizz` | Left eye winks closed with playful tilt; confident smirk mouth. | Warm Gold |

---

## 4. Setup & Deployment Instructions

1. Download the latest **MicroPython UF2 firmware for Raspberry Pi Pico** from [micropython.org](https://micropython.org/download/rp2-pico/).
2. Hold down the **BOOTSEL** button on the Pico while plugging the USB cable into your computer.
3. Drag and drop the `.uf2` file onto the mounted `RPI-RP2` drive.
4. Launch **Thonny IDE** and set the interpreter to **MicroPython (Raspberry Pi Pico)**.
5. Open `software/pico/src/main.py`.
6. Set live mode (line 33):
   ```python
   TESTING_MODE = False   # False = live UART from ESP32-CAM
   ```
7. In Thonny, choose **File -> Save As -> Raspberry Pi Pico** and save as **`main.py`**.
8. Disconnect USB and wire the Pico into the robot according to the [Hardware Pinout Matrix](pinout.md).
