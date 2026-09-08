# ADAM System Architecture Specification (v40)

## 1. Executive Summary

**ADAM (Autonomous Desktop AI Module)** is an embodied, multimodal AI desktop robot engineered by **[DGEN Technologies Pvt. Ltd.](https://dgentechnologies.com)** 

Unlike monolithic robotics architectures that attempt to execute high-level language models, computer vision, digital signal processing (DSP), hard real-time servo generation, and display rendering on a single system-on-chip, ADAM adopts a **specialized, distributed multi-tier architecture**. Each physical tier is assigned responsibilities based on hard hardware constraints, timing determinism, and electrical power budgets.

---

## 2. Multi-Tier Distributed Architecture Diagram

```mermaid
graph TD
    subgraph Cloud [Tier 1: Cloud Intelligence]
        GL[Google Gemini Live Multimodal API]
        STT_TTS[Bidirectional Voice & Vision WebSockets]
        GL <--> STT_TTS
    end

    subgraph Pi [Tier 2: Host Orchestrator - Raspberry Pi Zero 2 W]
        Main[main.py: Asyncio Supervised Event Loop]
        Session[session.py: Gemini Live Client & Turn Manager]
        AudioDSP[audio_utils.py: WOLA Suppressor, FIR Filter, Adaptive Gate & DOA]
        Link[esp32_link.py: High-Speed Binary UART Framing]
        Tools[tool_handler.py: Gemini Function Call Dispatcher]
        Mem[memory_store.py: Persistent User & Conversation Store]
        Vosk[Vosk Offline Wake-Word Engine]
        ServPan[hardware.py: Pan Servo on GPIO12 with Auto-Detach]

        Main --> Session
        Session <--> STT_TTS
        Session <--> AudioDSP
        Session <--> Link
        Session <--> Tools
        Session <--> Mem
        AudioDSP --> Vosk
        Session --> ServPan
    end

    subgraph ESP [Tier 3: Sensory & Peripheral Node - ESP32-CAM]
        OV[OV2640 Image Sensor + JPEG Engine]
        Touch[4x TTP223 Capacitive Touch Matrix]
        TiltPWM[Tilt Servo Controller on GPIO13]
        Relay[UART1 Protocol Stripper & Relay to Pico]
        
        OV --> Relay
        Touch --> Relay
        Relay --> TiltPWM
    end

    subgraph Pico [Tier 4: Face Display Engine - Raspberry Pi Pico RP2040]
        MicroPy[MicroPython 60 FPS Event Loop]
        ST7789[ST7789 2.4" 320x240 IPS Display @ 40MHz SPI]
        MicroPy --> ST7789
    end

    subgraph Workstation [Tier 5: Companion Host - Laptop Agent]
        Flask[Flask REST Server + Zeroconf mDNS Broadcast]
        ActionReg[Modular @action Registry & Tool Schemas]
        OSCtrl[OS Volume, Brightness, Apps, Spotify Controls]
        Flask --> ActionReg --> OSCtrl
    end

    %% Physical Interconnects
    Pi -- "I2S Subprocess Pipes (arecord/aplay)" --> VoiceHAT[Google voiceHAT Soundcard: 2x INMP441 & MAX98357A]
    Link -- "PL011 UART2 (/dev/serial0 @ 921600)" <--> Relay
    Relay -- "UART1 TX (GPIO3 @ 115200)" --> MicroPy
    Tools -- "LAN REST / mDNS (_adam-agent._tcp.local.)" <--> Flask
```

---

## 3. Tier-by-Tier Technical Breakdown

### Tier 1: Cloud Intelligence (Google Gemini Live)
- **Model**: `gemini-2.0-flash-exp` (or `gemini-3.1-flash-live`).
- **Protocol**: Bidirectional WebSockets over TLS to `wss://generativelanguage.googleapis.com`.
- **Audio Transmission**:
  - Inbound: Streaming raw 16kHz 16-bit mono linear PCM chunks.
  - Outbound: Streaming raw 24kHz PCM audio chunks with real-time text transcript fragments.
- **Turn-Taking**: ADAM utilizes manual activity detection (`MIC_VAD_HANGOVER_S=1.0`). Gemini receives `activity_end` explicitly when the local adaptive VAD gate closes after speech completion, eliminating mid-sentence turn chopping.

### Tier 2: Edge Brain (Raspberry Pi Zero 2 W)
- **OS**: Raspberry Pi OS 64-bit Lite (Debian 13 Trixie), Linux kernel 6.18+.
- **Process Model**: Single-process Python 3.13 asynchronous event loop (`asyncio`).
- **Audio I/O via ALSA Subprocess Pipes**:
  - Uses `arecord` (`S32_LE`, 48000 Hz, 2 channels) and `aplay` (`S16_LE`, 48000 Hz, 2 channels) spawned as subprocesses.
  - **Why subprocesses instead of PyAudio/sounddevice**: Subprocess pipes survive ALSA driver hardware wedges without crashing the Python interpreter. If the shared I2S clock peripheral drops into digital silence, ADAM automatically detects the dead stream and respawns `arecord` seamlessly.
- **Microphone Channel Selection (`_MicChannelLiveness`)**:
  - Dynamically measures the dynamic range ($20 \cdot \log_{10}(p99/p20)$) of both microphone channels over a 90-second sliding window.
  - If one channel has a hardware defect (such as the right mic on a hand-soldered board emitting white hiss), ADAM automatically drops the dead channel from the speech path, recovering **11.7 dB to 21 dB of signal-to-noise ratio (SNR)** in the critical consonant band (2 kHz – 8 kHz).
- **Acoustic Noise Suppression & Filtering**:
  - 80-tap FIR windowed-sinc filter bandpassed to human speech (150 Hz – 6800 Hz) followed by 3:1 decimation.
  - Weighted Overlap-Add (WOLA) spectral noise suppressor.
  - Adaptive VAD gate: opens on a **3-of-6 chunk quorum** (100 ms of voiced speech within a 200 ms window) with room-learned spectral flatness thresholding.
- **Servo Pan Actuation & Acoustic Decoupling**:
  - Direct PWM on GPIO 12 via `gpiozero.AngularServo`.
  - **Auto-Detach State Machine**: Once a pan move completes, the PWM signal is released after `NECK_SERVO_HOLD_S=0.6s`. This eliminates the 50Hz holding hum that mechanically couples into the INMP441 microphones and pins the voice gate open.

### Tier 3: Peripheral Node (AI-Thinker ESP32-CAM)
- **Processor**: Dual-Core Xtensa LX6 @ 240MHz with 4MB PSRAM.
- **Optics & Thermal Duty-Cycling**:
  - OV2640 camera sensor streaming hardware-compressed JPEG frames.
  - The camera is dynamically powered on (`CAM:ON` / `esp_camera_init()`) and de-initialized (`CAM:OFF` / `esp_camera_deinit()`) on demand, preventing thermal accumulation above 70°C.
- **Capacitive Touch Filtering**:
  - 4x TTP223 capacitive touch modules configured with solder jumper A **OPEN** (momentary mode).
  - 3-sample majority voting and 60ms state-change debounce filter to eliminate electrical noise on JTAG strapping pins (GPIO 14 / GPIO 15).
- **Dual Hardware UART Architecture**:
  - `UART2` (GPIO 4 TX, GPIO 16 RX): Interconnect to Pi GPIO 14/15 at 921,600 baud for camera frames and control commands.
  - `UART1` (GPIO 3 TX): One-way serial relay to Raspberry Pi Pico at 115,200 baud. Inbound `EMO:<emotion>\n` commands from the Pi have the prefix stripped and are forwarded as `<emotion>\n`.

### Tier 4: Expression Display (Raspberry Pi Pico RP2040)
- **Processor**: Dual-Core ARM Cortex-M0+ @ 133MHz.
- **Display**: 2.4" ST7789 IPS LCD (320x240) driven over 4-wire SPI at 40MHz.
- **Runtime**: MicroPython with a zero-heap runtime loop.
- **Graphics Pipeline**:
  - Contiguous 153.6 KB frame buffer allocated once at boot.
  - Big-endian RGB565 byte-swapping for ST7789 hardware alignment.
  - 14 distinct procedural vector emotional states with fluid organic eye drifts and blinks.

### Tier 5: Workstation Companion (Laptop Agent)
- **Execution**: Background Python service running on macOS, Windows, or Linux.
- **Discovery**: Announces `_adam-agent._tcp.local.` via Zeroconf (mDNS) on port 5000.
- **Action Registry**: Extensible `@action` decorator automatically exposes local workstation tools (audio volume, display brightness, screen lock, media playback, application launching) to Gemini Function Calling.

---

## 4. Fault Tolerance & Recovery Architecture

ADAM incorporates tested fault-recovery mechanisms developed through extensive field benchmarking:

| Subsystem Fault | Detection Signature | Automated Recovery Action |
| :--- | :--- | :--- |
| **I2S Capture Wedge (Fault A2)** | Continuous digital silence ($RMS = 0$) or flat signal for $>0.7\text{s}$ following playback close. | Subprocess watchdog terminates and respawns `arecord`, re-establishing ALSA I2S DMA. |
| **DNS Resolution Latency at Boot** | `socket.gaierror: [Errno -3]` during the first 60s of Wi-Fi association. | `adam.service` runs an `ExecStartPre` DNS readiness gate polling `generativelanguage.googleapis.com` before launching the main daemon. |
| **Dead Microphone Channel (Fault A8/A11)** | Low acoustic dynamic range ($<3\text{ dB}$ over 90s) while the opposing channel is responsive ($>8\text{ dB}$). | Channel selector automatically drops the dead channel, switching from `mix` to `left` mode and re-zeroing `.mic_floor.json`. |
| **Servo Hum Mic Interference** | Post-move RMS spike ($>3500$) above the VAD open threshold. | Software automatically detaches PWM pin 0.6s after move and enforces a 2.0s settling guard before allowing voice onset. |
| **ESP32 Disconnected / Unpowered** | `/dev/serial0` handshake times out. | ADAM logs a warning and enters **Audio-Only Mode**. Full conversational voice capabilities remain operational. |
