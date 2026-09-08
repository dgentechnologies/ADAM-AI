# Raspberry Pi Hardware Bring-Up & Configuration (v40)

Definitive, tested bring-up guide for **Raspberry Pi Zero 2 W** (and Raspberry Pi 4B) running ADAM v40 on **Debian 13 "Trixie" 64-bit**.

---

## 1. System Requirements & Hardware Specifications

- **Microcomputer**: Raspberry Pi Zero 2 W (Quad-Core Cortex-A53 @ 1.0GHz, 512MB RAM) or Raspberry Pi 4B.
- **Operating System**: Raspberry Pi OS (64-bit Lite, Debian 13 Trixie).
- **Soundcard**: Google voiceHAT I2S driver (`sndrpigooglevoi`) servicing dual INMP441 microphones and MAX98357A I2S amplifier.
- **Serial Interface**: Stable PL011 hardware UART mapped to `/dev/serial0` @ 921,600 baud.
- **Actuation**: Hardware PWM on GPIO 12 for Pan servo (`gpiozero.AngularServo`).

---

## 2. OS Provisioning (Raspberry Pi Imager)

1. Download and launch [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Select **Raspberry Pi OS (64-bit Lite)**.
3. In the **OS Customisation Settings** (`Ctrl+Shift+X`):
   - **Hostname**: `adam-pi`
   - **Username**: `pi`
   - **Password**: *Configure a secure password*
   - **Wireless LAN**: Enter your Wi-Fi SSID and Password. Set Country to your region (e.g. `IN`).
   - **Services**: Check **Enable SSH** (with password authentication or public key).
4. Flash onto a Class 10 / A2 microSD card (16GB+).

---

## 3. Kernel Configuration & Serial Port Setup

Insert the microSD card, boot the Pi, and SSH into it:
```bash
ssh pi@adam-pi.local
```

### A. Configure `/boot/firmware/config.txt`
Edit the boot configuration file:
```bash
sudo nano /boot/firmware/config.txt
```
Ensure the following directives are active:
```ini
# Enable low-level peripheral interfaces
dtparam=i2c_arm=on
dtparam=spi=on
dtparam=i2s=on
dtparam=audio=on

# Google voiceHAT driver: enumerates card "sndrpigooglevoi" for I2S capture & playback
dtoverlay=googlevoicehat-soundcard

# Expose hardware UART on GPIO14/15
enable_uart=1

# Disable Bluetooth: assigns the stable PL011 UART (/dev/ttyAMA0) to /dev/serial0
# (Prevents baud rate drift associated with the mini-UART / ttyS0 at 921,600 baud)
dtoverlay=disable-bt
```

### B. Free `/dev/serial0` from Linux Console
By default, Raspberry Pi OS attaches a serial login getty to `/dev/serial0`. Remove it so ADAM can communicate with the ESP32-CAM:

```bash
sudo sed -i 's/console=serial0,115200 //g' /boot/firmware/cmdline.txt
sudo systemctl disable --now serial-getty@ttyS0.service
sudo systemctl mask serial-getty@ttyS0.service
```

### C. Verify User Group Permissions
Ensure the `pi` user belongs to all necessary hardware groups:
```bash
sudo usermod -aG dialout,audio,gpio,spi,i2c pi
```

---

## 4. System Packages (APT)

Install ARM-native builds of NumPy, PySerial, GPIO, and ALSA tools so the Python environment does not need to compile C extensions on the Pi Zero 2 W:

```bash
sudo apt update && sudo apt install -y \
  python3-venv python3-dev python3-numpy python3-serial \
  python3-gpiozero python3-lgpio python3-requests \
  alsa-utils git unzip
```

---

## 5. Python Environment & Dependencies

Debian 13 adheres to PEP-668 ("externally managed environment"). You **must** install dependencies within a virtual environment. Create the venv **with system site-packages** to inherit native NumPy and GPIO libraries:

```bash
cd /home/pi
git clone https://github.com/dgentechnologies/ADAM-AI.git /home/pi/adam-repo

# Setup production runtime directory
mkdir -p /home/pi/adam
cp -r /home/pi/adam-repo/software/pi/src/* /home/pi/adam/

# Create virtual environment
python3 -m venv --system-site-packages /home/pi/adam/venv
/home/pi/adam/venv/bin/pip install --upgrade pip
/home/pi/adam/venv/bin/pip install google-genai websockets vosk zeroconf ddgs python-dotenv
```

Verify dependency resolution:
```bash
/home/pi/adam/venv/bin/python - <<'PY'
import importlib.util as u
for m in ["google.genai","websockets","vosk","zeroconf","ddgs","dotenv","numpy","serial","gpiozero","lgpio","requests"]:
    s = u.find_spec(m)
    print(f"{m:14}", "OK" if s else "MISSING", s.origin if s else "")
PY
```

---

## 6. Offline Vosk Wake-Word Model

Download the lightweight Vosk English speech model:
```bash
cd /home/pi/adam
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
rm vosk-model-small-en-us-0.15.zip
```
Creates `/home/pi/adam/vosk-model-small-en-us-0.15/` (~68 MB).

---

## 7. Zero 2 W Memory Optimization (Console Boot)

The Pi Zero 2 W has ~415 MB usable RAM. Booting directly to console (disabling the desktop GUI) frees ~100 MB of RAM, preventing swap thrashing (ADAM's peak RSS is ~140 MB):

```bash
sudo systemctl set-default multi-user.target
sudo systemctl disable lightdm.service
sudo reboot
```

---

## 8. Post-Boot Verification Checklist

After rebooting, confirm hardware enumeration:

```bash
# 1. Verify PL011 UART mapping
readlink -f /dev/serial0
# Expected output: /dev/ttyAMA0

# 2. Verify voiceHAT audio card
arecord -l ; aplay -l
# Expected: card 0 or 1: sndrpigooglevoi [snd_rpi_googlevoicehat_soundcar]

# 3. Audio round-trip test (records 2 seconds, plays back)
arecord -D plughw:sndrpigooglevoi,0 -f S32_LE -r 48000 -c 2 -d 2 /tmp/t.wav
aplay   -D plughw:sndrpigooglevoi,0 /tmp/t.wav ; rm /tmp/t.wav

# 4. Check memory headroom
free -h
# Swap used should be 0B
```

---

## 9. Production Systemd Service

Deploy the production self-healing systemd service:

```bash
sudo cp /home/pi/adam-repo/software/pi/adam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adam.service
sudo systemctl start adam.service
```

Monitor live logs:
```bash
journalctl -u adam.service -f -o cat
```
