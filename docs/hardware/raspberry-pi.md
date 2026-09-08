# Raspberry Pi Hardware Bring-Up & Configuration

This guide provides step-by-step instructions for provisioning and configuring the **Raspberry Pi Zero 2 W** (or Raspberry Pi 4B) as the host brain for ADAM.

---

## 1. Hardware Specifications

- **SoC**: Broadcom BCM2710A1, Quad-core 64-bit ARM Cortex-A53 @ 1.0 GHz
- **RAM**: 512MB LPDDR2 SDRAM
- **Connectivity**: 2.4GHz 802.11 b/g/n Wireless LAN, BLE 4.2
- **Audio Interfaces**: I2S Digital Audio Bus (integrated via Google voiceHAT driver)
- **Actuation**: Hardware PWM on GPIO12 (Pan servo)
- **Host Communications**: Dedicated PL011 UART (`/dev/serial0` @ 921,600 baud)

---

## 2. OS Provisioning (Debian 13 Trixie 64-bit)

Use the official [Raspberry Pi Imager](https://www.raspberrypi.com/software/):
1. **Operating System**: Choose **Raspberry Pi OS (64-bit Lite)**.
2. **OS Customisation Settings**:
   - **Hostname**: `adam-pi`
   - **Username**: `pi`
   - **Password**: *Configure a secure password*
   - **Wireless LAN**: Enter your Wi-Fi SSID, Password, and Country Code.
   - **Services**: Check **Enable SSH** (Use password authentication or your public SSH key).
3. Write the image to a high-speed microSD card (SanDisk Extreme Class 10 / A2 recommended, 32GB+).

---

## 3. Kernel & Device Tree Configuration

Insert the microSD card, boot the Pi, and SSH into it:
```bash
ssh pi@adam-pi.local
```

### Configure `/boot/firmware/config.txt`
Open the boot configuration file:
```bash
sudo nano /boot/firmware/config.txt
```
Ensure the following parameters are enabled:
```ini
# Enable hardware peripherals
dtparam=i2c_arm=on
dtparam=spi=on
dtparam=i2s=on
dtparam=audio=on

# VoiceHAT driver: enables dual INMP441 I2S capture + MAX98357A I2S playback
dtoverlay=googlevoicehat-soundcard

# Hardware UART: expose PL011 on GPIO14/15
enable_uart=1

# Disable Bluetooth: assigns the stable PL011 UART (/dev/ttyAMA0) to /dev/serial0
# (Prevents baud drift associated with the mini-UART / ttyS0 at 921,600 baud)
dtoverlay=disable-bt
```

### Free the Serial Port from the Console
By default, Raspberry Pi OS attaches a Linux login console (getty) to the primary serial port. To free `/dev/serial0` for high-speed communication with the ESP32-CAM:

1. Edit `/boot/firmware/cmdline.txt`:
   ```bash
   sudo nano /boot/firmware/cmdline.txt
   ```
2. Remove `console=serial0,115200` (leave `console=tty1` intact). Save and exit.
3. Disable the systemd serial getty service:
   ```bash
   sudo systemctl stop serial-getty@ttyAMA0.service
   sudo systemctl disable serial-getty@ttyAMA0.service
   sudo systemctl mask serial-getty@ttyAMA0.service
   ```
4. Reboot the Pi:
   ```bash
   sudo reboot
   ```

---

## 4. Hardware Verification

After rebooting, verify that all hardware devices enumerate correctly:

### Verify Sound Card (I2S VoiceHAT)
```bash
arecord -l
```
Expected output:
```text
card 0: sndrpigooglevoi [snd_rpi_googlevoicehat_soundcar], device 0: Google voiceHAT SoundCard HiFi voicehat-hifi-0 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

Verify playback:
```bash
aplay -l
```
Expected output:
```text
card 0: sndrpigooglevoi [snd_rpi_googlevoicehat_soundcar], device 0: Google voiceHAT SoundCard HiFi voicehat-hifi-0 []
```

### Test Microphone Audio Recording
Record 3 seconds of stereo test audio:
```bash
arecord -D plughw:CARD=sndrpigooglevoi,DEV=0 -f S32_LE -r 48000 -c 2 -d 3 test.wav
```
Playback the test audio through the speaker:
```bash
aplay -D plughw:CARD=sndrpigooglevoi,DEV=0 test.wav
```

### Verify UART Port
Check that `/dev/serial0` points to `ttyAMA0`:
```bash
ls -l /dev/serial0
```
Expected output:
```text
lrwxrwxrwx 1 root root 7 Sep 8 14:00 /dev/serial0 -> ttyAMA0
```

---

## 5. Installing the ADAM Software Stack

```bash
# Update repositories and install base audio/build tools
sudo apt update && sudo apt install -y git python3-pip python3-venv portaudio19-dev libasound2-dev libatlas-base-dev

# Clone ADAM AI
git clone https://github.com/dgentechnologies/ADAM-AI.git /home/pi/ADAM
cd /home/pi/ADAM/software/pi

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Systemd Auto-Start Service

To run ADAM continuously as a self-healing system service:
```bash
sudo cp adam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adam.service
sudo systemctl start adam.service
```

Check live logs:
```bash
sudo journalctl -u adam.service -f -n 50
```
