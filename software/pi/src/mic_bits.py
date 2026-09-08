#!/usr/bin/env python3
"""mic_bits.py — is the I2S stream real audio or misread bits?

Successive captures disagreed by 14 dB and swapped spectral character, which
acoustics cannot do.  Levels and spectra are both ambiguous evidence, but the
BIT LAYOUT is not: the INMP441 is a 24-bit mic clocked into a 32-bit slot, so
in a healthy stream

    bits 0-7    ALWAYS the same value (the mic never drives them)
    bit 31      the sign bit, ~50% only if the signal is symmetric and large
    high bits   fraction-of-ones falls off smoothly with bit position

If the SD line, BCLK or ground is marginal the receiver latches noise, and
EVERY bit position sits at ~50% — including the low 8 that no microphone can
reach.  That is a hardware verdict no amount of DSP can argue with.

Also reports:
  * whether L and R carry byte-identical samples (one slot wired to both)
  * how many DISTINCT values the low byte takes (1 = clean, 256 = garbage)
  * step-to-step jumps: real audio at 48 kHz is heavily oversampled and
    moves in small increments; random words jump full-scale every sample

Run it while ADAM is quiet, then again while sound is playing.  The bit
verdict must not change with sound; the level should.
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (CAPTURE_DEVICE, CAPTURE_FORMAT, CAPTURE_RATE,
                    CAPTURE_CHANNELS, CHUNK_FRAMES)
import audio_utils as au

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
CPS = CAPTURE_RATE / CHUNK_FRAMES

proc = subprocess.Popen(
    ["arecord", "-D", CAPTURE_DEVICE, "-f", CAPTURE_FORMAT,
     "-r", str(CAPTURE_RATE), "-c", str(CAPTURE_CHANNELS),
     "-t", "raw", "-q", "--buffer-size=48000"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
for _ in range(int(CPS)):
    au.read_exact(proc.stdout, CHUNK_BYTES)
raw = b"".join(au.read_exact(proc.stdout, CHUNK_BYTES)
               for _ in range(int(SECS * CPS)))
proc.terminate()

s32 = np.frombuffer(raw, dtype=np.int32)
L = s32[0::2]
R = s32[1::2]
n = min(L.size, R.size)
L, R = L[:n], R[:n]
print(f"{n} frames ({n/CAPTURE_RATE:.1f}s) @ {CAPTURE_RATE} Hz, "
      f"{CAPTURE_FORMAT}\n")

if np.array_equal(L, R):
    print("  *** L and R are BYTE-IDENTICAL — one word slot is feeding both "
          "channels ***\n")

u32 = s32.view(np.uint32)
UL, UR = u32[0::2][:n], u32[1::2][:n]

print("  fraction of samples where each bit is 1 "
      "(healthy: bits 0-7 all 0.00 or all 1.00)")
print(f"  {'bit':>5s} " + "".join(f"{b:5d}" for b in range(0, 12))
      + "   ...   " + "".join(f"{b:5d}" for b in range(24, 32)))
for nm, u in (("L", UL), ("R", UR)):
    lo = "".join(f"{np.mean((u >> b) & 1):5.2f}" for b in range(0, 12))
    hi = "".join(f"{np.mean((u >> b) & 1):5.2f}" for b in range(24, 32))
    print(f"  {nm:>5s} {lo}   ...   {hi}")

print()
for nm, x, u in (("L", L, UL), ("R", R, UR)):
    low8 = np.mean([np.mean((u >> b) & 1) for b in range(8)])
    nvals = len(np.unique(u & 0xFF))
    d = np.diff(x.astype(np.float64))
    jump = np.mean(np.abs(d)) / max(np.mean(np.abs(x.astype(np.float64) -
                                                  x.mean())), 1.0)
    verdict = ("GARBAGE — low 8 bits are random, this is not microphone data"
               if low8 > 0.15 and nvals > 64 else
               "clean bit layout — real 24-bit mic data")
    print(f"  {nm}: low-8-bit ones {low8:.3f}   distinct low bytes "
          f"{nvals:3d}/256   mean|step|/rms {jump:5.2f}")
    print(f"     -> {verdict}")

print("\n  mean|step|/rms near 1.4 means each sample is independent of the "
      "last\n  (random words). Real 48 kHz audio is oversampled: expect "
      "well under 1.0.")
