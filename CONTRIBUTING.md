# Contributing to ADAM AI

Thank you for your interest in contributing to **ADAM (Autonomous Desktop AI Module)**! 
ADAM is an open-source project by **DGEN Technologies Pvt. Ltd.** combining AI, embedded systems, and robotics.

Whether you are fixing a bug, adding an emotion to the Pico display, extending the Gemini tool definitions, or optimizing sound localization algorithms, your contributions are welcome.

---

## Code of Conduct

We expect all contributors to adhere to high standards of professionalism, respect, and constructive collaboration:
- Be respectful and welcoming to contributors of all backgrounds and skill levels.
- Focus on constructive code review and collaborative problem solving.
- Maintain electrical safety and mechanical precautions when proposing hardware modifications.

---

## How to Contribute

### 1. Reporting Issues
- Search existing GitHub Issues before opening a new one.
- Use a descriptive title and include clear reproduction steps, hardware versions, and log outputs.
- Specify whether the issue pertains to:
  - Software (`software/pi`, `software/laptop-agent`)
  - Firmware (`software/esp32-cam`, `software/pico`)
  - Hardware / Schematics (`docs/hardware/`)
  - Documentation / Examples (`docs/`, `examples/`)

### 2. Proposing Features
- Open a GitHub Discussion or Feature Request issue outlining the motivation, expected user experience, and technical approach before writing large pull requests.

### 3. Development Workflow
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/ADAM-AI.git
   cd ADAM-AI
   ```
3. Create a feature branch with a clear prefix:
   ```bash
   git checkout -b feat/gesture-recognition
   # or
   git checkout -b fix/uart-buffer-overflow
   ```
4. Follow code style rules (see below).
5. Verify changes locally on simulated or physical hardware.
6. Commit using [Conventional Commits](https://www.conventionalcommits.org/):
   ```text
   feat(pico): add surprised emotion eye animation
   fix(pi): resolve race condition in esp32 UART frame parser
   docs(hardware): correct I2S pin table for voiceHAT
   ```
7. Push to your fork and submit a Pull Request against `main`.

---

## Coding Standards

### Python (`software/pi`, `software/laptop-agent`, `examples/`)
- Target **Python 3.11+** (compatible up to 3.13).
- Follow **PEP 8** style guidelines. Format using `black` and `ruff`.
- Use type hints (`typing.Optional`, `typing.Dict`, etc.) wherever feasible.
- Ensure asynchronous code properly handles task cancellation and exception propagation.
- Keep dependency additions minimal and well-justified.

### Arduino C++ (`software/esp32-cam/`)
- Write clean, non-blocking Arduino code.
- Avoid using `delay()` inside `loop()` — use `millis()` timers for state transitions and debouncing.
- Keep baud rates synchronized with Pi configurations (default: `921600` for UART2, `115200` for Pico relay).
- Verify memory consumption; avoid memory fragmentation by pre-allocating buffers for camera frames.

### MicroPython (`software/pico/`)
- Minimize runtime memory allocations to prevent `MemoryError` on the RP2040.
- Frame buffers for display drawing should be pre-allocated once during boot.
- Keep animation math lightweight (use integer coordinates and lookup tables where appropriate).

---

## Hardware Testing Protocols

Because ADAM involves physical actuators, voltages, and sensors, verify your hardware modifications against:
1. **Voltage Compatibility**: Ensure no 5V signal is ever sent to 3.3V logic pins on the Pi or Pico without a level shifter.
2. **Current Draw**: Verify that high-draw components (servos, camera flash) do not share an unbuffered rail with microcontroller logic to prevent brownout resets.
3. **Duty Cycling**: Any continuous camera capture routine must provide a thermal sleep or duty-cycle mechanism.

---

## License Notice
By contributing to ADAM AI, you agree that your contributions will be licensed under the project's **Apache 2.0 License**.
