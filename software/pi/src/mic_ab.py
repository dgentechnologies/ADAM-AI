#!/usr/bin/env python3
"""mic_ab.py — A/B the noise bed against the things that could be making it.

The ambient probe showed a noise bed whose LOUDEST octave is 5-8 kHz
(31.6% of total energy, 52.8% above 3.4 kHz). That is not a room; rooms
are low-frequency. This script tests the two candidate sources that are
under software control, and records raw captures so the suppressor can be
A/B'd offline on the real noise:

  A  nothing running                      (baseline)
  B  aplay holding the playback device open on silence
     -> the voiceHAT class-D amp is powered and switching
  C  aplay open AND actually playing a speech file
     -> speech through air, the only stimulus available without a person

Writes /tmp/mic_A.raw /tmp/mic_B.raw /tmp/mic_C.raw (S32_LE 48k stereo).
"""
import os
import sys
import math
import subprocess
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (CAPTURE_DEVICE, CAPTURE_FORMAT, CAPTURE_RATE,
                    CAPTURE_CHANNELS, CHUNK_FRAMES, PLAYBACK_DEVICE,
                    GEMINI_SEND_RATE)
import audio_utils as au

CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
NFFT = 1024
WIN = np.hanning(NFFT).astype(np.float32)
FRQ = np.fft.rfftfreq(NFFT, 1.0 / GEMINI_SEND_RATE)
BANDS = [(100, 300), (300, 1000), (1000, 2000), (2000, 3400),
         (3400, 5000), (5000, 8000)]


def capture(secs, path):
    p = subprocess.Popen(
        ["arecord", "-D", CAPTURE_DEVICE, "-f", CAPTURE_FORMAT,
         "-r", str(CAPTURE_RATE), "-c", str(CAPTURE_CHANNELS),
         "-t", "raw", "-q", "--buffer-size=48000"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    for _ in range(12):
        au.read_exact(p.stdout, CHUNK_BYTES)
    n = int(secs * CAPTURE_RATE / CHUNK_FRAMES)
    blob = bytearray()
    for _ in range(n):
        blob += au.read_exact(p.stdout, CHUNK_BYTES)
    p.terminate()
    with open(path, "wb") as f:
        f.write(bytes(blob))
    return bytes(blob)


def analyse(label, blob):
    au._mic_chain.__init__()          # fresh filter state per case
    rms, pwr = [], None
    for i in range(0, len(blob) - CHUNK_BYTES + 1, CHUNK_BYTES):
        pcm = au.s32_stereo_to_s16_mono_16k(blob[i:i + CHUNK_BYTES])
        x = np.frombuffer(pcm, np.int16).astype(np.float32)
        rms.append(float(np.sqrt(np.mean(x ** 2))))
        buf = np.zeros(NFFT, np.float32)
        m = min(x.size, NFFT)
        buf[:m] = (x[:m] - x[:m].mean()) * WIN[:m]
        P = np.abs(np.fft.rfft(buf)) ** 2 + 1e-12
        pwr = P if pwr is None else pwr + P
    a = np.array(rms)
    Pm = pwr / max(len(rms), 1)
    tot = Pm.sum()
    parts = " ".join(f"{100*Pm[(FRQ>=lo)&(FRQ<hi)].sum()/tot:5.1f}"
                     for lo, hi in BANDS)
    print(f"  {label:34s} rms p50 {np.percentile(a,50):6.0f}  "
          f"p90 {np.percentile(a,90):6.0f}  max {a.max():6.0f} | {parts}")
    return a, Pm


print("bands: " + " ".join(f"{lo//100 if lo<1000 else lo//1000}"
                           f"{'h' if lo<1000 else 'k'}-"
                           f"{hi//1000 if hi>=1000 else hi//100}"
                           f"{'k' if hi>=1000 else 'h'}"
                           for lo, hi in BANDS))
print()

# ── A: baseline ──────────────────────────────────────────────────────
print("A: baseline (nothing running)")
A = capture(6.0, "/tmp/mic_A.raw")

# ── B: playback device open on digital silence ───────────────────────
print("B: aplay open on silence (amp powered)")
zero = subprocess.Popen(["dd", "if=/dev/zero", "bs=192000", "count=40"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
ap = subprocess.Popen(["aplay", "-D", PLAYBACK_DEVICE, "-f", "S16_LE",
                       "-r", "48000", "-c", "2", "-t", "raw", "-q",
                       "--buffer-size=9600", "--period-size=2400"],
                      stdin=zero.stdout, stderr=subprocess.DEVNULL)
time.sleep(1.0)
B = capture(6.0, "/tmp/mic_B.raw")
for p in (ap, zero):
    try:
        p.terminate()
    except Exception:
        pass
time.sleep(1.0)

# ── C: speech through the speaker, if a reference file exists ────────
C = None
wav = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "hello_adam_16k.wav")
if os.path.exists(wav):
    print("C: hello_adam_16k.wav through the speaker")
    loop = subprocess.Popen(
        ["sh", "-c", f"for i in 1 2 3 4 5 6 7 8; do aplay -q -D "
                     f"{PLAYBACK_DEVICE} {wav}; done"],
        stderr=subprocess.DEVNULL)
    time.sleep(0.6)
    C = capture(6.0, "/tmp/mic_C.raw")
    try:
        loop.terminate()
    except Exception:
        pass
    subprocess.run(["pkill", "-f", "aplay"], stderr=subprocess.DEVNULL)

print("\n                                     "
      "                        | % of energy per band")
aA, pA = analyse("A baseline", A)
aB, pB = analyse("B amp open, silence", B)
if C is not None:
    aC, pC = analyse("C speech through speaker", C)

print(f"\n  B/A broadband rms delta: "
      f"{20*math.log10(np.percentile(aB,50)/max(np.percentile(aA,50),1)):+.1f} dB")
for lo, hi in BANDS:
    msk = (FRQ >= lo) & (FRQ < hi)
    d = 10 * math.log10(max(pB[msk].sum(), 1e-9) / max(pA[msk].sum(), 1e-9))
    print(f"    {lo:5d}-{hi:<5d} Hz  {d:+6.1f} dB")
