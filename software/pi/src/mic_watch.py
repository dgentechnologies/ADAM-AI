#!/usr/bin/env python3
"""mic_watch.py — per-channel level and spectral tilt over time.

Two successive `mic_probe.py --left` runs minutes apart disagreed by 14 dB
and the HF hiss signature moved from the right channel onto the left one.
Either the noise bed is not stationary or a connection is intermittent, and
those need different fixes, so this watches BOTH channels continuously and
prints one line per second:

    level per channel (dBFS, raw S32, DC removed)
    HF fraction per channel = energy above 3.4 kHz as % of 0.1-8 kHz
      -> the dead/floating-line signature is a high HF fraction, because
         bus noise is white while room noise and speech are not

A channel flipping between regimes is a hardware intermittency; both
channels drifting together is the room.  Run for as long as you can.
"""
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (CAPTURE_DEVICE, CAPTURE_FORMAT, CAPTURE_RATE,
                    CAPTURE_CHANNELS, CHUNK_FRAMES)
import audio_utils as au

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
CPS = CAPTURE_RATE / CHUNK_FRAMES
FS32 = 2.0 ** 31
NF = 2048
W = np.hanning(NF)
F = np.fft.rfftfreq(NF, 1.0 / CAPTURE_RATE)
BAND = (F >= 100) & (F < 8000)
HF = (F >= 3400) & (F < 8000)

proc = subprocess.Popen(
    ["arecord", "-D", CAPTURE_DEVICE, "-f", CAPTURE_FORMAT,
     "-r", str(CAPTURE_RATE), "-c", str(CAPTURE_CHANNELS),
     "-t", "raw", "-q", "--buffer-size=48000"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
for _ in range(12):
    au.read_exact(proc.stdout, CHUNK_BYTES)

print(" t(s) |   L dBFS  L HF%  |   R dBFS  R HF%  |  R-L dB  | note")
acc = {0: [], 1: []}
hfa = {0: [], 1: []}
seen = []
for k in range(int(SECS * CPS)):
    s32 = np.frombuffer(au.read_exact(proc.stdout, CHUNK_BYTES), dtype=np.int32)
    for i in (0, 1):
        ch = s32[i::2].astype(np.float64)
        ch = ch - ch.mean()
        acc[i].append(math.sqrt(float(np.dot(ch, ch)) / max(ch.size, 1)))
        buf = np.zeros(NF)
        m = min(ch.size, NF)
        buf[:m] = ch[:m] * W[:m]
        P = np.abs(np.fft.rfft(buf)) ** 2 + 1e-12
        hfa[i].append(100.0 * P[HF].sum() / max(P[BAND].sum(), 1e-12))
    if (k + 1) % int(CPS):
        continue
    t = (k + 1) / CPS
    dl = 20 * math.log10(max(np.mean(acc[0]), 1) / FS32)
    dr = 20 * math.log10(max(np.mean(acc[1]), 1) / FS32)
    hl, hr = np.mean(hfa[0]), np.mean(hfa[1])
    note = []
    if hl > 40: note.append("L hissy")
    if hr > 40: note.append("R hissy")
    print(f"{t:5.0f} | {dl:+8.1f} {hl:6.1f}  | {dr:+8.1f} {hr:6.1f}  |"
          f" {dr-dl:+7.1f}  | {' '.join(note)}")
    seen.append((dl, dr, hl, hr))
    acc = {0: [], 1: []}
    hfa = {0: [], 1: []}

proc.terminate()
a = np.array(seen)
print("\n              min     p50     max    spread")
for j, nm in ((0, "L dBFS"), (1, "R dBFS"), (2, "L HF%"), (3, "R HF%")):
    c = a[:, j]
    print(f"  {nm:8s} {c.min():7.1f} {np.median(c):7.1f} {c.max():7.1f} "
          f"{c.max()-c.min():7.1f}")
print("\n  A spread over ~6 dB on a channel's level, or an HF% that moves "
      "between\n  regimes, is an intermittent connection — not a room.")
