# ADAM Host Core Software (Raspberry Pi v40)

The `software/pi` package contains the core orchestration software running on the **Raspberry Pi Zero 2 W** (or Raspberry Pi 4/5). It coordinates real-time multimodal streaming with Google Gemini Live, manages I2S audio capture/playback via ALSA subprocess pipes, runs the WOLA noise suppressor and GCC-PHAT sound localization, and communicates with the ESP32-CAM over high-speed UART.

---

## 📂 Source Code Structure

```text
software/pi/
├── README.md               # Architecture and operational guide (this file)
├── requirements.txt        # Python package dependencies
├── adam.service            # Production systemd daemon unit with DNS gate
└── src/
    ├── main.py             # Main entry point, argument parsing & supervised reconnect loop
    ├── session.py          # Gemini Live bidirectional WebSocket session manager
    ├── config.py           # Single source of truth for pins, rates, and buffers
    ├── audio_utils.py      # ALSA pipes, 80-tap FIR filter, WOLA noise suppressor, adaptive VAD
    ├── esp32_link.py       # High-speed UART binary framing & command handler
    ├── hardware.py         # Direct GPIO PWM servo panning controller with auto-detach
    ├── laptop_agent_client.py # Local LAN companion agent discovery & client
    ├── memory_store.py     # Local JSON persistent user profile & conversation memory
    ├── system_prompt.py    # Personality definition, constraints, and instructions
    ├── SystemPrompt.txt    # Base prompt instructions and operational rules
    ├── song_playback.py    # Paced WAV audio playback with spoken stop phrase support
    ├── tool_handler.py     # Function call executor (web search, laptop, emotions)
    ├── tools_schema.py     # OpenAPI-compatible schemas for Gemini tool declarations
    ├── web_search.py       # Async DuckDuckGo search integration
    ├── ws_server.py        # Local WebSocket relay for dashboard telemetry
    ├── heartbeat.py        # System health metrics and watchdog monitoring
    ├── watchdog.py         # Self-recovery mechanism for deadlocks
    │
    └── Audio Diagnostics:
        ├── mic_probe.py    # ADC saturation, energy distribution, and in-band SNR
        ├── mic_modes.py    # Multi-channel acoustic evaluator on identical captures
        ├── mic_cause.py    # Distinguishes acoustic noise from CPU ripple or dead channels
        ├── mic_bits.py     # Verifies I2S 24-bit alignment and data framing
        ├── mic_watch.py    # Long-term channel level and spectral tilt drift monitor
        ├── mic_geom.py     # Inter-microphone delay and cross-channel coherence
        └── nr_bench.py     # Noise suppressor benchmarking against clean references
```

---

## 🛠️ Setup & Deployment Instructions

### 1. System Requirements
- Raspberry Pi Zero 2 W or Pi 4B running **Raspberry Pi OS 64-bit Lite (Debian 13 Trixie)**.
- Working I2S soundcard configured (`googlevoicehat-soundcard`).
- PL011 UART enabled (`/dev/serial0` freed from login console).

### 2. Deployment to `/home/pi/adam`
On the Raspberry Pi, deploy the runtime files into `/home/pi/adam`:
```bash
mkdir -p /home/pi/adam
cp -r src/* /home/pi/adam/
cd /home/pi/adam
```

### 3. Virtual Environment & Dependencies
```bash
python3 -m venv --system-site-packages venv
venv/bin/pip install --upgrade pip
venv/bin/pip install google-genai websockets vosk zeroconf ddgs python-dotenv
```

### 4. Vosk Wake-Word Model
```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
rm vosk-model-small-en-us-0.15.zip
```

### 5. Environment Configuration
Create `/home/pi/adam/.env`:
```bash
cat > /home/pi/adam/.env << 'EOF'
GEMINI_API_KEY=your_gemini_api_key_here
ENABLE_IDLE=0
EOF
chmod 600 /home/pi/adam/.env
```

### 6. Production Systemd Service
```bash
sudo cp ../adam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adam.service
sudo systemctl start adam.service

# Follow live output
journalctl -u adam.service -f -o cat
```
