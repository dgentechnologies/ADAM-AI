# ADAM Developer Examples & Testing Utilities

This directory contains standalone testing scripts, hardware simulation harnesses, and developer extension recipes.

---

## 🛠️ Included Utilities

### 1. `mock_esp32_serial.py` — Hardware-Free Serial Simulator
Emulates the AI-Thinker ESP32-CAM over a serial link:
- Generates synthetic JPEG camera frames and packages them in ADAM's binary `'F'` framing.
- Simulates capacitive cheek touch events (`T1:1\n`) and petting gestures.
- Logs incoming tilt (`TILT:90\n`), camera power (`CAM:ON\n`), and relayed emotion (`EMO:happy\n`) commands.

**Usage:**
```bash
python examples/mock_esp32_serial.py
```

---

### 2. `test_audio_doa.py` — Acoustic Direction-of-Arrival (DOA) Verification
Mathematically validates the Generalized Cross-Correlation with Phase Transform (GCC-PHAT) algorithm:
- Simulates stereo audio signals captured across two microphones separated by $d = 65\text{ mm}$.
- Computes time-difference-of-arrival (TDOA) down to microsecond precision.
- Converts delay to angular azimuth (-90° to +90°) and compares against ground truth angles.

**Usage:**
```bash
python examples/test_audio_doa.py
```

---

### 3. `custom_action_plugin.py` — Extending the Laptop Companion Agent
Demonstrates how to add custom skills to the Laptop Agent using the `@action` decorator:
- Shows how to declare tool parameters and descriptions.
- Provides real-world examples: controlling Philips Hue smart desk lights and updating Slack presence.

**Usage:**
```bash
python examples/custom_action_plugin.py
```
