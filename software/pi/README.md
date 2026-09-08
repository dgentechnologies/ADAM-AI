# ADAM Host Core Software (Raspberry Pi)

The `software/pi` package contains the core orchestration software running on the **Raspberry Pi Zero 2 W** (or Raspberry Pi 4/5). It coordinates multimodal streaming with Google Gemini Live, handles I2S audio capture/playback, runs GCC-PHAT sound localization, and communicates with the ESP32-CAM over high-speed UART.

---

## 📂 Source Code Structure

```text
software/pi/
├── README.md               # Architecture and setup guide
├── requirements.txt        # Python package dependencies
├── adam.service            # Systemd service unit definition
└── src/
    ├── main.py             # Main entry point & top-level reconnect loop
    ├── session.py          # Gemini Live bidirectional WebSocket session manager
    ├── config.py           # Single source of truth for pins, rates, and buffers
    ├── audio_utils.py      # ALSA pipes, audio format DSP, and GCC-PHAT DOA
    ├── esp32_link.py       # High-speed UART binary framing & command handler
    ├── hardware.py         # Direct GPIO PWM servo panning controller
    ├── laptop_agent_client.py # Local LAN companion agent discovery & client
    ├── memory_store.py     # Local JSON persistent user profile & conversation memory
    ├── system_prompt.py    # Personality definition, constraints, and instructions
    ├── tool_handler.py     # Function call executor (web search, laptop, emotions)
    ├── tools_schema.py     # OpenAPI-compatible schemas for Gemini tool declarations
    ├── web_search.py       # Async DuckDuckGo search integration
    ├── ws_server.py        # Local WebSocket relay for dashboard telemetry
    ├── heartbeat.py        # System health metrics and watchdog monitoring
    └── watchdog.py         # Self-recovery mechanism for deadlocks
```

---

## 🛠️ Setup Instructions

### 1. System Requirements
- Raspberry Pi Zero 2 W or Pi 4B running **Raspberry Pi OS 64-bit Lite (Debian 13 Trixie)**.
- Working I2S soundcard configured (`googlevoicehat-soundcard`).
- PL011 UART enabled (`/dev/serial0` freed from login console).

### 2. Python Virtual Environment
```bash
cd /home/pi/ADAM/software/pi
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```bash
cp ../../.env.example /home/pi/ADAM/.env
nano /home/pi/ADAM/.env
```
Ensure `GOOGLE_API_KEY` is populated with a valid Gemini API key.

### 4. Running the Software
```bash
python src/main.py
```

### 5. Running as a System Service
```bash
sudo cp adam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adam.service
sudo systemctl start adam.service

# Check logs
sudo journalctl -u adam.service -f -n 50
```
