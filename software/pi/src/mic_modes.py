#!/usr/bin/env python3
"""mic_modes.py — score left / right / mix on ONE identical capture.

Two `mic_probe.py` runs with MIC_CHANNEL=left, minutes apart, disagreed by
14 dB and swapped spectral character.  Separate captures cannot settle that:
the room may have changed, or the env override may not have taken effect.

So this captures once and pushes the SAME bytes through
`s32_stereo_to_s16_mono_16k` three times, forcing the selector to each mode
in turn, and prints the resulting int16 level and band split.  Any difference
is then attributable to the channel choice and nothing else.

It also prints the selector's own live measurement (first-difference RMS
dynamic range per channel) so the decision and the evidence appear together.
"""
import os
import sys
import subprocess

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (CAPTURE_DEVICE, CAPTURE_FORMAT, CAPTURE_RATE,
                    CAPTURE_CHANNELS, CHUNK_FRAMES, GEMINI_SEND_RATE,
                    S32_SHIFT, MIC_CHANNEL)
import audio_utils as au

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
CPS = CAPTURE_RATE / CHUNK_FRAMES
NF = 1024
W = np.hanning(NF)
F = np.fft.rfftfreq(NF, 1.0 / GEMINI_SEND_RATE)
BANDS = [(100, 300), (300, 1000), (1000, 2000), (2000, 3400),
         (3400, 5000), (5000, 8000)]

proc = subprocess.Popen(
    ["arecord", "-D", CAPTURE_DEVICE, "-f", CAPTURE_FORMAT,
     "-r", str(CAPTURE_RATE), "-c", str(CAPTURE_CHANNELS),
     "-t", "raw", "-q", "--buffer-size=48000"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
for _ in range(int(CPS)):                       # 1 s of warm-up, discarded
    au.read_exact(proc.stdout, CHUNK_BYTES)
chunks = [au.read_exact(proc.stdout, CHUNK_BYTES)
          for _ in range(int(SECS * CPS))]
proc.terminate()

print(f"MIC_CHANNEL={MIC_CHANNEL!r}  S32_SHIFT={S32_SHIFT}  "
      f"{len(chunks)/CPS:.1f}s, one capture scored three ways\n")

hdr = "".join(
    (f"{lo//1000 if lo >= 1000 else lo}{'k' if lo >= 1000 else ''}-"
     f"{hi//1000 if hi >= 1000 else hi}{'k' if hi >= 1000 else ''}").rjust(9)
    for lo, hi in BANDS)
print(f"{'mode':6s} {'p50':>7s} {'p90':>7s} {'in-band p50':>12s} | {hdr}")

rows = {}
for mode in ("left", "right", "mix"):
    au._mic_live.forced = True                  # freeze the selector
    au._mic_live.mode = mode
    au._mic_chain.__init__()                    # clear filter history
    rms, ib, pw = [], [], None
    for c in chunks:
        x = np.frombuffer(au.s32_stereo_to_s16_mono_16k(c),
                          dtype=np.int16).astype(np.float32)
        rms.append(float(np.sqrt(np.mean(x * x))))
        buf = np.zeros(NF, np.float32)
        m = min(x.size, NF)
        buf[:m] = (x[:m] - x[:m].mean()) * W[:m]
        P = np.abs(np.fft.rfft(buf)) ** 2 + 1e-12
        ib.append(float(P[(F >= 300) & (F < 3400)].sum()))
        pw = P if pw is None else pw + P
    tot = pw.sum()
    parts = "".join(f"{100*pw[(F >= lo) & (F < hi)].sum()/tot:8.1f}%"
                    for lo, hi in BANDS)
    rows[mode] = np.percentile(rms, 50)
    print(f"{mode:6s} {np.percentile(rms, 50):7.0f} "
          f"{np.percentile(rms, 90):7.0f} {np.percentile(ib, 50):12.0f} | "
          f"{parts}")

print(f"\n  right - left  {20*np.log10(max(rows['right'], 1)/max(rows['left'], 1)):+.1f} dB"
      f"      mix - left  {20*np.log10(max(rows['mix'], 1)/max(rows['left'], 1)):+.1f} dB")

# ── what the shipping selector would have decided on this same audio ──
sel = au._MicChannelLiveness()
sel.forced = False
sel.seen_live = [False, False]        # cold start: ignore any persisted state
sel.seen_dead = [False, False]
sel.dr = [0.0, 0.0]
sel._apply()
for c in chunks:
    s32 = np.frombuffer(c, dtype=np.int32)
    sel.observe(s32[0::2].astype(np.float32), s32[1::2].astype(np.float32))
print(f"\n  selector after {len(chunks)/CPS:.0f}s: mode={sel.mode!r} "
      f"seen_live={sel.seen_live} seen_dead={sel.seen_dead}  "
      f"dynamic range L {sel.dr[0]:+.1f} dB / R {sel.dr[1]:+.1f} dB")
print("  (live needs >=MIC_CH_LIVE_DR_DB absolute; deaf needs only the "
      "relative\n  margin, so silence alone is enough to condemn a channel)")
