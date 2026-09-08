#!/usr/bin/env python3
"""mic_cause.py — is the noise bed acoustic, or is it the Pi's power rail?

Established so far on this unit: the I2S bit layout is clean (low 8 bits of
every 32-bit word are exactly zero, so the words are real 24-bit mic samples,
not misread bits), yet the bed is near-white, uncorrelated between the two
mics, and has been measured anywhere from -39 to -25 dBFS minutes apart.

Acoustics cannot do that.  Two mics centimetres apart in one head share a
sound field, so a genuine room bed is strongly coherent below ~1 kHz.  Zero
coherence at every frequency means the noise is generated inside each mic
independently -- which on a hand-soldered board means the 3V3 rail and the
ground return.  The Pi Zero 2 W regulates with a switcher whose ripple tracks
CPU current draw, so that hypothesis makes a sharp prediction: load the CPU
and the noise floor rises, with no sound in the room at all.

Three phases, one process, so nothing can drift between them:

  1 IDLE     baseline level + L<->R coherence
  2 LOADED   same, with every core spinning
  3 SOUND    same, with broadband noise out of ADAM's own speaker

Read it like this:
  * level rises from 1 to 2 with no sound      -> power/ground, not the room
  * coherence stays ~0 in 1 and 2, rises in 3  -> mics are fine, bed is
                                                  electrical, speech is real
  * a channel that does not move in phase 3    -> that mic really is dead
"""
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (CAPTURE_DEVICE, CAPTURE_FORMAT, CAPTURE_RATE,
                    CAPTURE_CHANNELS, CHUNK_FRAMES, PLAYBACK_DEVICE,
                    PLAYBACK_RATE)
import audio_utils as au

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
CPS = CAPTURE_RATE / CHUNK_FRAMES
FS32 = 2.0 ** 31
NF = 2048
W = np.hanning(NF)
FRQ = np.fft.rfftfreq(NF, 1.0 / CAPTURE_RATE)
BANDS = [(100, 300), (300, 1000), (1000, 2000), (2000, 3400),
         (3400, 5000), (5000, 8000)]


def capture(secs):
    proc = subprocess.Popen(
        ["arecord", "-D", CAPTURE_DEVICE, "-f", CAPTURE_FORMAT,
         "-r", str(CAPTURE_RATE), "-c", str(CAPTURE_CHANNELS),
         "-t", "raw", "-q", "--buffer-size=48000"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    for _ in range(int(CPS)):
        au.read_exact(proc.stdout, CHUNK_BYTES)
    raw = b"".join(au.read_exact(proc.stdout, CHUNK_BYTES)
                   for _ in range(int(secs * CPS)))
    proc.terminate()
    proc.wait()
    s32 = np.frombuffer(raw, dtype=np.int32)
    return s32[0::2].astype(np.float64), s32[1::2].astype(np.float64)


def analyse(l, r):
    hop = NF // 2
    Saa = np.zeros(NF // 2 + 1)
    Sbb = np.zeros(NF // 2 + 1)
    Sab = np.zeros(NF // 2 + 1, dtype=complex)
    k = 0
    for i in range(0, min(len(l), len(r)) - NF + 1, hop):
        A = np.fft.rfft((l[i:i + NF] - l[i:i + NF].mean()) * W)
        B = np.fft.rfft((r[i:i + NF] - r[i:i + NF].mean()) * W)
        Saa += np.abs(A) ** 2
        Sbb += np.abs(B) ** 2
        Sab += A * np.conj(B)
        k += 1
    g2 = np.clip(np.abs(Sab) ** 2 / np.maximum(Saa * Sbb, 1e-20), 0.0, 1.0)
    dl = 20 * math.log10(max(math.sqrt(np.mean((l - l.mean()) ** 2)), 1) / FS32)
    dr = 20 * math.log10(max(math.sqrt(np.mean((r - r.mean()) ** 2)), 1) / FS32)
    # coherence below 1 kHz is where two co-located mics MUST agree
    lowc = float(g2[(FRQ >= 100) & (FRQ < 1000)].mean())
    return dl, dr, lowc, Saa / max(k, 1), Sbb / max(k, 1), 1.0 / max(k, 1)


def bandpow(s):
    return np.array([max(s[(FRQ >= lo) & (FRQ < hi)].sum(), 1e-12)
                     for lo, hi in BANDS])


hdr = "".join(
    (f"{lo//1000 if lo >= 1000 else lo}{'k' if lo >= 1000 else ''}-"
     f"{hi//1000 if hi >= 1000 else hi}{'k' if hi >= 1000 else ''}").rjust(9)
    for lo, hi in BANDS)

res = {}

# ── 1 IDLE ──────────────────────────────────────────────────────────────
print(f"1 IDLE     ({SECS:.0f}s, silence, no extra load)")
res["idle"] = analyse(*capture(SECS))

# ── 2 LOADED ────────────────────────────────────────────────────────────
ncpu = os.cpu_count() or 4
print(f"2 LOADED   ({SECS:.0f}s, silence, {ncpu} spinning cores)")
load = [subprocess.Popen(["sh", "-c", "while :; do :; done"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL) for _ in range(ncpu)]
try:
    res["loaded"] = analyse(*capture(SECS))
finally:
    for p in load:
        p.terminate()
    for p in load:
        p.wait()

# ── 3 SOUND ─────────────────────────────────────────────────────────────
print(f"3 SOUND    ({SECS:.0f}s, broadband noise from ADAM's speaker)")
rng = np.random.default_rng(1)
tone = rng.normal(0, 6000, int(PLAYBACK_RATE * (SECS + 2.5)))
tone = np.clip(tone, -32768, 32767).astype(np.int16).tobytes()
play = subprocess.Popen(
    ["aplay", "-D", PLAYBACK_DEVICE, "-f", "S16_LE",
     "-r", str(PLAYBACK_RATE), "-c", "1", "-t", "raw", "-q"],
    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL)
try:
    play.stdin.write(tone)
    play.stdin.flush()
except Exception:
    pass
try:
    res["sound"] = analyse(*capture(SECS))
finally:
    try:
        play.stdin.close()
    except Exception:
        pass
    play.terminate()
    play.wait()

# ── report ──────────────────────────────────────────────────────────────
print(f"\n{'phase':9s} {'L dBFS':>8s} {'R dBFS':>8s} {'R-L':>6s} "
      f"{'coh<1k':>7s} {'floor':>7s}")
for k in ("idle", "loaded", "sound"):
    dl, dr, c, _, _, cf = res[k]
    flag = "  <- at the estimator floor: TRULY uncorrelated" if c < 3 * cf else ""
    print(f"{k:9s} {dl:+8.1f} {dr:+8.1f} {dr-dl:+6.1f} {c:7.3f} {cf:7.3f}{flag}")

print(f"\nlevel change per band (dB)\n          {hdr}")
for label, a, b in (("load-idle", "idle", "loaded"),
                    ("sound-idle", "idle", "sound")):
    for ch, ix in (("L", 3), ("R", 4)):
        d = 10 * np.log10(bandpow(res[b][ix]) / bandpow(res[a][ix]))
        print(f"  {label:10s} {ch} " + "".join(f"{v:+8.1f} " for v in d))

dl_i, dr_i = res["idle"][0], res["idle"][1]
dl_l, dr_l = res["loaded"][0], res["loaded"][1]
print("\nverdict")
if max(dl_l - dl_i, dr_l - dr_i) > 2.0:
    print(f"  CPU load raised the noise floor by "
          f"{max(dl_l-dl_i, dr_l-dr_i):+.1f} dB with NO sound in the room.")
    print("  The bed is conducted through the 3V3 rail / ground return, not "
          "acoustic.\n  No amount of DSP fixes this — it needs decoupling at "
          "the mic and a\n  star ground back to the Pi. Software can only "
          "avoid making it worse.")
else:
    print("  CPU load did not move the noise floor; the bed is not "
          "load-dependent.")
