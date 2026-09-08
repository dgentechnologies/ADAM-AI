# ADAM Development & Diagnostic Engineering Guide (v40)

This guide provides testing methodologies, diagnostic tool documentation, and real-world troubleshooting references based on physical prototype measurements.

---

## 1. Local Workstation Setup & Simulation

Developers can test Gemini Live integration, laptop agent capabilities, and signal processing on a personal computer without physical microcontrollers:

```bash
git clone https://github.com/dgentechnologies/ADAM-AI.git
cd ADAM-AI

# Create virtual environment
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r software/pi/requirements.txt
```

### A. Simulating the ESP32-CAM Serial Bus
Run `examples/mock_esp32_serial.py` to emulate the ESP32-CAM's camera frames, touch events, and tilt/emotion command execution:
```bash
python examples/mock_esp32_serial.py
```

### B. Testing the Laptop Companion Agent
```bash
cd software/laptop-agent
pip install -r requirements.txt
python src/laptop_agent.py
```
Query self-describing tool schemas:
```bash
curl http://localhost:5000/actions
```

---

## 2. Reading Live System Logs & Mic Telemetry

On the Raspberry Pi, follow live service logs:
```bash
journalctl -u adam.service -f -o cat
```

### Deciphering the Mic Stats Telemetry Line
Every 20 seconds, ADAM logs a structured acoustic telemetry report:
```text
📊 Mic 20s: p50 1150 p90 2100 p99 2900 max 3400 | open≥2470 hold≥1730 | floor 1082 flat 0.31/0.35 lohi 1.90 shp 40% | opens 4 sent 118 | blocked 2 | nr -10.9dB | shut
```

- **`p50 / p90 / p99 / max`**: Post-filter int16 RMS distribution across the 20s window.
- **`open≥ / hold≥`**: Active VAD thresholds calculated dynamically from the learned floor.
- **`floor`**: Current learned room noise floor ($p20$ of the recent 45s window).
- **`flat 0.31/0.35`**: Measured spectral flatness of the current chunk / live adaptive threshold.
- **`lohi`**: Low-frequency vs high-frequency energy ratio.
- **`shp`**: Percentage of recent chunks that passed the voiced spectral shape test.
- **`opens`**: Total gate openings in this 20s window.
- **`sent`**: Number of audio chunks transmitted to Gemini Live.
- **`blocked`**: Onset attempts that decayed without achieving the 3-of-6 chunk quorum.
- **`nr`**: Mean noise suppression gain across the 300 Hz – 3400 Hz speech band.
- **`mode`**: Gate state (`shut`, `OPEN`, `IDLE`, `SONG`), plus `+AMP` if floor tracking is paused during audio playback.

---

## 3. Dedicated Audio Diagnostic Suite

The `software/pi/src/` directory includes specialized diagnostic tools designed to test hardware channels without re-implementing signal pipelines:

| Script | Purpose & Diagnostic Question Answered |
| :--- | :--- |
| **`mic_probe.py [seconds]`** | Measures ADC saturation, energy distribution, and in-band SNR. |
| **`mic_modes.py [seconds]`** | Evaluates `left`, `right`, and `mix` channels on a single identical audio capture to determine optimal channel routing. |
| **`mic_cause.py [seconds]`** | Determines whether noise is acoustic, CPU-conducted ripple, or an ungrounded dead channel. |
| **`mic_bits.py [seconds]`** | Verifies 24-bit I2S bit alignment and detects dropped byte errors. |
| **`mic_watch.py [seconds]`** | Monitors per-channel level and spectral tilt over time to identify intermittent cold solder joints. |
| **`mic_geom.py`** | Computes inter-microphone delay and L/R acoustic coherence. |
| **`nr_bench.py`** | Benchmarks noise suppressor candidates against clean acoustic references. |

---

## 4. Hardware & Acoustic Triage Reference

| What You Observe | Root Cause | Authoritative Remedy |
| :--- | :--- | :--- |
| **"Hello ADAM" $\rightarrow$ "Hello madam"; consonants corrupted** | Right microphone is dead on the Vero board; averaging in `mix` mode destroys consonant SNR by 11–21 dB. | Verify continuity of right mic `SD` pin to Pi GPIO 20. Ensure `MIC_CHANNEL=auto` is set so software drops the dead channel. |
| **ADAM talks spontaneously (idle nudge) but cannot hear you** | Trapped in idle mode or gate threshold set above quiet speech. | Set `ENABLE_IDLE=0` in `.env`. Ensure `MIC_VAD_ONSET_CHUNKS=3` and `MIC_VAD_ONSET_WINDOW=6`. |
| **ADAM stops hearing you ~1 second after it finishes talking** | Shared I2S clock peripheral entered digital silence (I2S capture wedge). | Automated in `session.py`: watchdog detects zero-RMS run and respawns `arecord` subprocess. |
| **Answers half your sentence, then answers the second half** | VAD hangover time too short, mistaking natural breathing pauses for end of turn. | Set `MIC_VAD_HANGOVER_S=1.0` in `.env`. |
| **Continuous loud buzzing during speaker playback** | Byte-alignment corruption on unbuffered `aplay` pipe. | Resolved in `audio_utils.py`: pipe writes are buffered and aligned to 4-byte sample boundaries. |
| **Voice volume jumps around randomly** | MAX98357A `GAIN` pin is floating. | Solder a pull-down resistor from `GAIN` to `GND` on the amplifier board (sets fixed 9dB gain). |
| **Pi reboots or restarts when head moves** | Servos drawing current from the Pi logic rail, causing brownout. | Wire servos to the dedicated 5V Actuator Rail with a $1000\mu\text{F}$ low-ESR capacitor. |
| **`socket.gaierror: Temporary failure in name resolution` at boot** | Pi starts before local router DNS resolver is responsive. | `adam.service` includes an `ExecStartPre` DNS readiness gate polling Google servers. |
