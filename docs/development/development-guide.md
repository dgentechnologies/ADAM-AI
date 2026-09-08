# ADAM Development & Engineering Guide

This guide outlines the local development workflows, hardware simulation strategies, debugging tools, and testing methodologies for ADAM.

---

## 1. Local Workstation Setup

You can develop and test major parts of ADAM (Gemini Live integration, function calling, Laptop Agent actions, and audio DSP) on your PC or Mac without physical microcontrollers.

### Clone the Repository
```bash
git clone https://github.com/dgentechnologies/ADAM-AI.git
cd ADAM-AI
```

### Python Virtual Environment Setup
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r software/pi/requirements.txt
```

---

## 2. Hardware-Free Simulation & Testing

When physical Raspberry Pi Zero or ESP32 hardware is not connected, ADAM can be tested using simulated virtual serial ports:

### A. Simulating the ESP32-CAM Serial Link
The script `examples/mock_esp32_serial.py` creates a virtual loopback that emulates the ESP32-CAM's UART protocol:
- Periodically sends fake JPEG camera frames.
- Simulates capacitive cheek touches and petting gestures.
- Receives and logs incoming `TILT:`, `CAM:`, and `EMO:` commands.

Run the mock serial generator in a dedicated terminal:
```bash
python examples/mock_esp32_serial.py
```

### B. Testing the Laptop Companion Agent
1. Navigate to `software/laptop-agent`:
   ```bash
   cd software/laptop-agent
   pip install -r requirements.txt
   python src/laptop_agent.py
   ```
2. In another terminal, query the agent's self-describing action schema:
   ```bash
   curl http://localhost:5000/actions
   ```
3. Test triggering a system action:
   ```bash
   curl -X POST http://localhost:5000/control \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer change_this_secret_token_in_production" \
     -d '{"action": "set_volume", "params": {"level": 50}}'
   ```

---

## 3. Remote Development on Raspberry Pi

For physical hardware bring-up, use **VS Code Remote - SSH**:
1. Install the **Remote - SSH** extension in VS Code.
2. Press `F1` and select `Remote-SSH: Connect to Host...`.
3. Enter `pi@adam-pi.local`.
4. Open the workspace folder `/home/pi/ADAM`.
5. You can now edit files directly on the Pi, launch debuggers, and monitor live serial telemetry in the integrated terminal.

---

## 4. Diagnostic & Inspection Commands

### Monitor Real-Time Systemd Service Logs
```bash
sudo journalctl -u adam.service -f -o cat
```

### Monitor Serial Bus Activity
Inspect raw incoming packets from the ESP32-CAM using `minicom` or Python:
```bash
# Install minicom
sudo apt install -y minicom

# Open connection @ 921,600 baud
minicom -b 921600 -D /dev/serial0
```

### Check I2S Audio Buffer Status
```bash
cat /proc/asound/card0/pcm0p/sub0/status
```

### Check Raspberry Pi Core Temperature & Throttling Status
```bash
vcgencmd measure_temp
vcgencmd get_throttled
# 0x0 indicates clean operation without under-voltage or thermal throttling
```

---

## 5. Troubleshooting Common Issues

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| `serial.serialutil.SerialException: [Errno 13] Permission denied: '/dev/serial0'` | The `pi` user does not belong to the `dialout` group. | Run `sudo usermod -a -G dialout pi` and re-login. |
| Camera frame corrupted or `F` header missing | Baud rate mismatch or electrical noise on UART lines. | Ensure both Pi and ESP32 baud rates match (`921600`). Verify solid ground connection. If jumper wires exceed 15cm, reduce baud rate to `460800`. |
| Pi reboots unexpectedly when speaking or moving head | Electrical brownout caused by servo inrush current or audio amp draw. | Verify servos are powered from the independent 5V actuator rail. Install a $1000\mu\text{F}$ capacitor across servo power rails. |
| ALSA `Device or resource busy` | Another process (e.g. Pulseaudio or old `arecord` instance) holds the soundcard. | Kill lingering audio processes: `sudo pkill -9 arecord; sudo pkill -9 aplay`. |
