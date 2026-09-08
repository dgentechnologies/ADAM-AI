#!/usr/bin/env python3
"""mic_probe.py — one-shot measurement of the real capture path on this unit.

Answers exactly four questions, all of which decide the mic fix:

  1. Does the ADC saturate?  (raw S32, per channel, before every filter —
     the one defect no DSP downstream can repair)
  2. Where is the energy?    (fraction below 60/120/300 Hz; the subsonic
     rumble is what eats the converter headroom)
  3. Does the int16 stage    (mono48 -> /2**S32_SHIFT -> clip) saturate?
  4. What is the in-band SNR (300-3400 Hz) that Gemini actually receives,
     and what does AdaptiveGate think of it?

Run with no argument for an ambient capture; pass seconds to change the
length. Prints a per-second table plus a summary. Uses the REAL
audio_utils/config so the numbers describe the shipped pipeline, not a
re-implementation of it.
"""
import os
import sys
import math
import subprocess

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (CAPTURE_DEVICE, CAPTURE_FORMAT, CAPTURE_RATE,
                    CAPTURE_CHANNELS, CHUNK_FRAMES, S32_SHIFT, MIC_HP_HZ,
                    MIC_CHANNEL, GEMINI_SEND_RATE, ENABLE_EXPANDER,
                    MIC_NR)
import audio_utils as au

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
FS32 = 2.0 ** 31
CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
CHUNKS_PER_S = CAPTURE_RATE / CHUNK_FRAMES          # 30.0

print(f"S32_SHIFT={S32_SHIFT}  MIC_HP_HZ={MIC_HP_HZ}  MIC_CHANNEL={MIC_CHANNEL}"
      f"  MIC_NR={MIC_NR}  ENABLE_EXPANDER={ENABLE_EXPANDER}")
print(f"capture {CAPTURE_DEVICE} {CAPTURE_FORMAT} {CAPTURE_RATE}Hz "
      f"{CAPTURE_CHANNELS}ch, chunk {CHUNK_FRAMES} frames "
      f"({1000.0/CHUNKS_PER_S:.1f} ms)\n")

proc = subprocess.Popen(
    ["arecord", "-D", CAPTURE_DEVICE, "-f", CAPTURE_FORMAT,
     "-r", str(CAPTURE_RATE), "-c", str(CAPTURE_CHANNELS),
     "-t", "raw", "-q", "--buffer-size=48000"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)

# warm-up discard (the first ~0.4 s off this HAT is garbage)
for _ in range(12):
    au.read_exact(proc.stdout, CHUNK_BYTES)

n_chunks = int(SECS * CHUNKS_PER_S)

raw_peak = [0.0, 0.0]
raw_clip = [0, 0]
raw_dc_acc = [0.0, 0.0]
raw_sq_acc = [0.0, 0.0]
n_samp = 0

i16_clip = 0
i16_total = 0

rms_hist = []
inband_hist = []
lf_hist = []
flat_hist = []
lohi_hist = []
spk_hist = []
pwr_acc = None

# 1024-pt analysis on the 16 kHz signal, matching AdaptiveGate's grid
NFFT = 1024
WIN = np.hanning(NFFT).astype(np.float32)
FRQ = np.fft.rfftfreq(NFFT, 1.0 / GEMINI_SEND_RATE)
B_SUB = FRQ < 120.0
B_IN = (FRQ >= 300.0) & (FRQ <= 3400.0)
B_FRIC = (FRQ > 3400.0)

# 4096-pt analysis on the 48 kHz raw signal, to see the rumble itself
NF48 = 4096
W48 = np.hanning(NF48).astype(np.float32)
F48 = np.fft.rfftfreq(NF48, 1.0 / CAPTURE_RATE)

print(" t(s)  rawL_pk  rawR_pk  clipL clipR | i16rms i16clip | "
      "sub120%  in300_3400%  fric%  | flat  lohi | floor  open  spk")

sec_rows = []
for k in range(n_chunks):
    raw = au.read_exact(proc.stdout, CHUNK_BYTES)
    s32 = np.frombuffer(raw, dtype=np.int32)
    l = s32[0::2].astype(np.float64)
    r = s32[1::2].astype(np.float64)
    n_samp += l.size
    for i, ch in ((0, l), (1, r)):
        raw_peak[i] = max(raw_peak[i], float(np.abs(ch).max()))
        raw_clip[i] += int(np.count_nonzero(np.abs(ch) >= 0.98 * FS32))
        raw_dc_acc[i] += float(ch.sum())
        raw_sq_acc[i] += float((ch ** 2).sum())

    # exact shipped conversion
    pcm = au.s32_stereo_to_s16_mono_16k(raw)
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    i16_total += x.size
    i16_clip += int(np.count_nonzero(np.abs(x) >= 32767))
    rms = float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0
    rms_hist.append(rms)

    buf = np.zeros(NFFT, np.float32)
    m = min(x.size, NFFT)
    buf[:m] = (x[:m] - x[:m].mean()) * WIN[:m]
    P = np.abs(np.fft.rfft(buf)) ** 2 + 1e-12
    pwr_acc = P if pwr_acc is None else pwr_acc + P
    tot = P.sum()
    sub = P[B_SUB].sum() / tot
    inb = P[B_IN].sum() / tot
    fric = P[B_FRIC].sum() / tot
    inband_hist.append(math.sqrt(P[B_IN].sum()))
    lf_hist.append(sub)

    spk = au._adaptive_gate.is_speech(pcm, rms)
    au._adaptive_gate.observe_background(rms, pcm)
    flat_hist.append(au._adaptive_gate.flat)
    lohi_hist.append(au._adaptive_gate.lohi)
    spk_hist.append(spk)

    if (k + 1) % int(CHUNKS_PER_S) == 0:
        t = (k + 1) / CHUNKS_PER_S
        j0 = k + 1 - int(CHUNKS_PER_S)
        print(f"{t:5.0f}  "
              f"{20*math.log10(max(raw_peak[0],1)/FS32):+7.1f}  "
              f"{20*math.log10(max(raw_peak[1],1)/FS32):+7.1f}  "
              f"{raw_clip[0]:5d} {raw_clip[1]:5d} | "
              f"{np.mean(rms_hist[j0:]):6.0f} {i16_clip:7d} | "
              f"{100*np.mean(lf_hist[j0:]):7.1f}  {100*inb:11.1f}  "
              f"{100*fric:5.1f}  | "
              f"{np.mean(flat_hist[j0:]):.3f} {np.mean(lohi_hist[j0:]):5.2f} | "
              f"{au._adaptive_gate.floor:5.0f} {au._adaptive_gate.open_th:5.0f}  "
              f"{sum(spk_hist[j0:]):2d}/{len(spk_hist[j0:])}")

proc.terminate()

rms_a = np.array(rms_hist)
inb_a = np.array(inband_hist)
print("\n── raw S32, per channel (before every filter) ────────────────────")
for i, name in ((0, "L"), (1, "R")):
    dc = raw_dc_acc[i] / n_samp
    rms32 = math.sqrt(raw_sq_acc[i] / n_samp)
    print(f"  {name}: peak {20*math.log10(max(raw_peak[i],1)/FS32):+6.1f} dBFS   "
          f"rms {20*math.log10(max(rms32,1)/FS32):+6.1f} dBFS   "
          f"dc {dc:+.3e} ({20*math.log10(max(abs(dc),1)/FS32):+.1f} dBFS)   "
          f"saturated samples {raw_clip[i]} "
          f"({100.0*raw_clip[i]/n_samp:.4f}%)")
print(f"  headroom left on the loudest sample: "
      f"{-max(20*math.log10(max(raw_peak[0],1)/FS32), 20*math.log10(max(raw_peak[1],1)/FS32)):.1f} dB")

print("\n── int16 stage (mono / 2**S32_SHIFT, clipped) ────────────────────")
print(f"  saturated int16 samples: {i16_clip} of {i16_total} "
      f"({100.0*i16_clip/max(i16_total,1):.4f}%)  <-- nonzero means "
      f"MIC_S32_SHIFT is too small")

print("\n── level distribution of what Gemini receives (int16 RMS) ────────")
for p in (5, 20, 50, 90, 99):
    print(f"  p{p:<2d} {np.percentile(rms_a, p):8.0f}")
print(f"  max {rms_a.max():8.0f}")

print("\n── in-band (300-3400 Hz) magnitude ──────────────────────────────")
for p in (5, 20, 50, 90, 99):
    print(f"  p{p:<2d} {np.percentile(inb_a, p):10.0f}")
lo, hi = np.percentile(inb_a, 20), np.percentile(inb_a, 95)
print(f"  p95/p20 in-band ratio = {20*math.log10(hi/max(lo,1e-9)):+.1f} dB "
      f"(this is the SNR the recogniser sees)")

print("\n── average spectrum of the whole capture, 16 kHz path ───────────")
Pm = pwr_acc / n_chunks
tot = Pm.sum()
bands = [(0, 60), (60, 120), (120, 300), (300, 1000), (1000, 2000),
         (2000, 3400), (3400, 5000), (5000, 8000)]
for a, b in bands:
    msk = (FRQ >= a) & (FRQ < b)
    print(f"  {a:5d}-{b:<5d} Hz  {100*Pm[msk].sum()/tot:6.2f}%")
kmax = int(np.argmax(Pm[1:]) + 1)
print(f"  loudest component: {FRQ[kmax]:.1f} Hz")

print(f"\n  gate: floor {au._adaptive_gate.floor:.0f}  "
      f"open_th {au._adaptive_gate.open_th:.0f}  "
      f"strong_th {au._adaptive_gate.strong_th:.0f}  "
      f"flat_max {au._adaptive_gate.flat_max:.3f}  "
      f"backend {au._adaptive_gate.backend}")
print(f"  chunks the gate called speech: {sum(spk_hist)}/{len(spk_hist)} "
      f"({100.0*sum(spk_hist)/max(len(spk_hist),1):.1f}%)")
