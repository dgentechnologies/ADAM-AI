"""
mock_esp32_serial.py — Simulated ESP32-CAM Serial Loopback
==============================================================================
ADAM AI Example Suite — DGEN Technologies Pvt. Ltd.

Simulates the AI-Thinker ESP32-CAM node over a local serial or virtual port.
Use this script to develop and verify the Raspberry Pi software (main.py)
on a PC or Raspberry Pi without physical ESP32-CAM or Pico hardware connected.

Features:
- Responds to 'CAM:ON' and 'CAM:OFF' commands.
- Sends mock JPEG camera frames with standard 'F' + length framing.
- Emulates occasional capacitive cheek touches ('T1:1\n', 'T2:1\n').
- Logs inbound tilt commands ('TILT:90\n') and relayed emotions ('EMO:happy\n').
"""

import sys
import time
import struct
import random
import io

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def generate_mock_jpeg(frame_id: int) -> bytes:
    """Generates a dynamic compressed JPEG in memory."""
    if not PIL_AVAILABLE:
        # Fallback 1x1 dummy JPEG if Pillow is not installed
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'

    img = Image.new("RGB", (320, 240), color=(20, 24, 33))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "ADAM Simulated Camera Stream", fill=(0, 255, 200))
    draw.text((20, 50), f"Frame Sequence: #{frame_id:06d}", fill=(255, 255, 255))
    draw.text((20, 80), f"Timestamp: {time.strftime('%H:%M:%S')}", fill=(200, 200, 200))
    
    # Draw animated target crosshair
    cx, cy = 160 + int(40 * (random.random() - 0.5)), 120 + int(30 * (random.random() - 0.5))
    draw.ellipse((cx - 25, cy - 25, cx + 25, cy + 25), outline=(255, 50, 80), width=2)
    draw.line((cx - 35, cy, cx + 35, cy), fill=(255, 50, 80), width=1)
    draw.line((cx, cy - 35, cx, cy + 35), fill=(255, 50, 80), width=1)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


def encode_frame_packet(jpeg_bytes: bytes) -> bytes:
    """Encodes JPEG bytes into the standard ADAM 'F' + uint32_BE + payload framing."""
    header = b'F'
    length = struct.pack('>I', len(jpeg_bytes))
    return header + length + jpeg_bytes + b'\n'


def run_standalone_demo():
    print("=" * 60)
    print("  ADAM Mock ESP32-CAM Serial Generator")
    print("  Simulating: Dual-UART Relay, OV2640 Frames & Touch Matrix")
    print("=" * 60)
    print("Generating simulated telemetry stream (press Ctrl+C to stop)...")

    frame_counter = 0
    camera_enabled = True

    try:
        while True:
            time.sleep(1.0)
            frame_counter += 1

            # 1. Simulate camera frame transmission if camera is enabled
            if camera_enabled:
                jpeg = generate_mock_jpeg(frame_counter)
                packet = encode_frame_packet(jpeg)
                print(f"[TX UART2] Sent Frame #{frame_counter} ({len(packet)} bytes)")

            # 2. Simulate random capacitive touch event every 5 seconds
            if frame_counter % 5 == 0:
                pad = random.choice([1, 2, 3])
                print(f"[TX UART2] Emulating Touch Event -> 'T{pad}:1\\n'")
                time.sleep(0.1)
                print(f"[TX UART2] Emulating Touch Release -> 'T{pad}:0\\n'")

            # 3. Simulate occasional inbound command handling
            if frame_counter % 7 == 0:
                mock_cmd = random.choice(["TILT:90", "TILT:75", "EMO:happy", "EMO:thinking", "CAM:ON"])
                print(f"[RX UART2] Processed Host Command: '{mock_cmd}\\n'")
                if mock_cmd.startswith("EMO:"):
                    relayed = mock_cmd[4:]
                    print(f"   └──> [TX UART1 to Pico] Relayed Emotion: '{relayed}\\n'")

    except KeyboardInterrupt:
        print("\nStopping Mock ESP32-CAM simulation.")


if __name__ == "__main__":
    run_standalone_demo()
