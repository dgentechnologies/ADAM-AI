#!/usr/bin/env python3
"""nr_bench.py — how much of the consonant band can be recovered, measured.

The noise bed on this unit is stationary, uncorrelated between the two
mics, and HF-tilted (loudest octave 5-8 kHz).  Speech is LF-dominated.
That combination admits two different suppressors, and this benchmarks
both against a KNOWN clean reference so the numbers are true SNR, not
estimates:

  clean  = hello_adam_16k.wav  (the digital source — no noise in it)
  noise  = /tmp/mic_A.raw      (the real bed, straight off this HAT)
  mix    = clean scaled to a chosen broadband SNR + real noise

  (1) the shipped single-channel WOLA suppressor (_NoiseSuppressor),
      swept over oversub x floor_db
  (2) a dual-mic coherence Wiener filter — magnitude-squared coherence
      between L and R is SNR/(1+SNR) per bin when the noise is
      uncorrelated and the source is not, which is exactly this hardware

Reports per-band SNR before/after and the speech distortion each one
costs, plus CPU per 33.3 ms chunk.
"""
import os
import sys
import math
import time
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (GEMINI_SEND_RATE, CHUNK_FRAMES, CAPTURE_CHANNELS,
                    MIC_NR_FRAME, MIC_NR_NOISE_S, MIC_NR_SMOOTH)
import audio_utils as au

HERE = os.path.dirname(os.path.abspath(__file__))
CHUNK_BYTES = CHUNK_FRAMES * CAPTURE_CHANNELS * 4
HOP16 = 533                                   # samples per 33.3 ms chunk @16k
BANDS = [(100, 300), (300, 1000), (1000, 2000), (2000, 3400),
         (3400, 5000), (5000, 8000)]
NFFT = 512
WIN = np.hanning(NFFT).astype(np.float32)
FRQ = np.fft.rfftfreq(NFFT, 1.0 / GEMINI_SEND_RATE)
MASK = [(FRQ >= lo) & (FRQ < hi) for lo, hi in BANDS]


def band_power(x: np.ndarray) -> np.ndarray:
    """Average power per band over the whole signal."""
    acc = np.zeros(len(BANDS))
    n = 0
    for i in range(0, len(x) - NFFT + 1, NFFT // 2):
        seg = x[i:i + NFFT] * WIN
        P = np.abs(np.fft.rfft(seg)) ** 2
        for b, m in enumerate(MASK):
            acc[b] += P[m].sum()
        n += 1
    return acc / max(n, 1)


def load_noise_mono(path):
    """Real bed through the real capture chain, per channel and mixed."""
    blob = open(path, "rb").read()
    s32 = np.frombuffer(blob, dtype=np.int32)
    l32, r32 = s32[0::2], s32[1::2]

    def chain(mono48):
        ch = au._MicChain()
        return ch.process(mono48.astype(np.float32)) / float(1 << au.S32_SHIFT)

    return chain(l32), chain(r32), chain((l32 + r32) * 0.5)


def load_clean():
    w = wave.open(os.path.join(HERE, "hello_adam_16k.wav"))
    assert w.getframerate() == GEMINI_SEND_RATE and w.getnchannels() == 1
    return np.frombuffer(w.readframes(w.getnframes()),
                         np.int16).astype(np.float32)


nl, nr, nm = load_noise_mono("/tmp/mic_A.raw")
clean0 = load_clean()

# Tile the clean utterance and the noise to a common length.
N = min(len(nm), len(nl), len(nr))
reps = int(math.ceil(N / len(clean0)))
clean = np.tile(clean0, reps)[:N]
nl, nr, nm = nl[:N], nr[:N], nm[:N]

# Active-speech RMS (frames above 20% of peak), so the target SNR refers
# to speech, not to the silence between repetitions.
env = np.array([np.sqrt(np.mean(clean[i:i + HOP16] ** 2))
                for i in range(0, N - HOP16, HOP16)])
act = env > 0.20 * env.max()
sp_rms = float(np.sqrt(np.mean(np.concatenate(
    [clean[i * HOP16:(i + 1) * HOP16] ** 2
     for i in range(len(env)) if act[i]]))))
nz_rms = float(np.sqrt(np.mean(nm ** 2)))

TARGET_SNR_DB = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
k = (nz_rms * 10 ** (TARGET_SNR_DB / 20.0)) / sp_rms
clean = clean * k
sp_rms *= k

print(f"noise bed rms {nz_rms:.0f}   speech scaled to active rms "
      f"{sp_rms:.0f}  → broadband SNR {TARGET_SNR_DB:+.1f} dB")
print(f"length {N/GEMINI_SEND_RATE:.1f}s\n")

# Speech arrives at both mics correlated; the bed is the real, genuinely
# uncorrelated per-channel noise.  MIC_LAG is the inter-mic delay in 16 kHz
# samples (endfire, 65 mm -> 189 us -> 3 samples); pass it as argv[2] to
# model a different talker angle.  0 = broadside, no comb.
MIC_LAG = int(sys.argv[2]) if len(sys.argv) > 2 else 3


def lag(x, d):
    return x if d <= 0 else np.concatenate((np.zeros(d, np.float32), x[:-d]))


sp_l, sp_r = clean, lag(clean, MIC_LAG)
sp_m = (sp_l + sp_r) * 0.5
mix_l = sp_l + nl
mix_r = sp_r + nr
mix_m = (mix_l + mix_r) * 0.5
print(f"inter-mic lag modelled: {MIC_LAG} samples @16k "
      f"({1e6*MIC_LAG/GEMINI_SEND_RATE:.0f} us"
      + (f", L+R comb null at {GEMINI_SEND_RATE/(2*MIC_LAG):.0f} Hz)"
         if MIC_LAG else ", no comb)"))

hdr = "  " + " " * 28 + "".join(f"{lo//1000 if lo>=1000 else lo}"
                                f"{'k' if lo>=1000 else ''}-"
                                f"{hi//1000 if hi>=1000 else hi}"
                                f"{'k' if hi>=1000 else ''}".rjust(11)
                               for lo, hi in BANDS)

base = None            # set from the un-processed mono mix below


def eval_out(label, y, cost_ms=None):
    """True SNR after processing: least-squares-project y onto clean to split
    it into a scaled-signal part and an error part, then band-power both.
    Both the WOLA suppressor and the coherence filter are zero-delay
    (output sample i comes from input sample i), so no realignment."""
    global base
    m = min(len(y), len(clean))
    yy, cc = y[:m], clean[:m]
    a = float(np.dot(yy, cc) / max(np.dot(cc, cc), 1e-9))   # best scale
    err = yy - a * cc
    snr = 10 * np.log10(band_power(a * cc) / np.maximum(band_power(err), 1e-9))
    print(f"  {label:28s}" + "".join(f"{v:+10.1f} " for v in snr)
          + (f"   {cost_ms:.2f} ms/chunk" if cost_ms else ""))
    if base is None:
        base = snr
    else:
        d = snr - base
        print(" " * 30 + "".join(f"{'('+format(v,'+.1f')+')':>10} " for v in d)
              + f"   300-3400 Δ {np.mean(d[1:4]):+.1f} dB,"
                f" 2-8k Δ {np.mean(d[3:]):+.1f} dB")
    return snr


print("band SNR, true (signal vs error against the clean reference):")
print(hdr)
eval_out("mono mix — TODAY", mix_m)


# ── (0) null control: WOLA analysis/synthesis with no spectral change ─
# If the harness is aligned and COLA holds, this MUST score 0.0 dB in
# every band. Any other result means the numbers below are meaningless.
def wola_identity(x, nfft=512):
    hop = nfft // 2
    w = np.sqrt(np.hanning(nfft + 1)[:nfft]).astype(np.float32)
    acc = np.zeros(nfft, np.float32)
    out = []
    for i in range(0, len(x) - nfft + 1, hop):
        seg = np.fft.irfft(np.fft.rfft(x[i:i + nfft] * w), nfft)
        acc += seg.astype(np.float32) * w
        out.append(acc[:hop].copy())
        acc = np.concatenate((acc[hop:], np.zeros(hop, np.float32)))
    return np.concatenate(out) if out else np.zeros(0, np.float32)


_null = eval_out("null control (must be 0.0)", wola_identity(mix_m))
if np.max(np.abs(_null - base)) > 0.5:
    print("\n  !! harness is misaligned — the null control is not 0.0 dB."
          "\n     Every row below is invalid. Fix before drawing conclusions.")

# ── (1) shipped single-channel WOLA suppressor ───────────────────────
best = None
for oversub in (1.5, 2.0, 2.5, 3.0, 3.5):
    for fdb in (-18.0, -12.0):
        ns = au._NoiseSuppressor(MIC_NR_FRAME, oversub, fdb,
                                 MIC_NR_NOISE_S, GEMINI_SEND_RATE,
                                 smooth=MIC_NR_SMOOTH)
        out = bytearray()
        t0 = time.perf_counter()
        nch = 0
        for i in range(0, len(mix_m) - HOP16 + 1, HOP16):
            seg = np.clip(mix_m[i:i + HOP16], -32768, 32767)
            out += ns.process(seg.astype(np.int16).tobytes())
            nch += 1
        cost = (time.perf_counter() - t0) * 1000.0 / max(nch, 1)
        y = np.frombuffer(bytes(out), np.int16).astype(np.float32)
        snr = eval_out(f"WOLA oversub={oversub} fl={fdb:.0f}", y, cost)
        sc = np.mean(snr[3:] - base[3:])
        if best is None or sc > best[0]:
            best = (sc, oversub, fdb)

# ── (2) dual-mic coherence Wiener filter ─────────────────────────────
def coherence_wiener(xl, xr, nfft=512, alpha=0.85, gmin_db=-18.0,
                     hop=None):
    hop = hop or nfft // 2
    w = np.sqrt(np.hanning(nfft + 1)[:nfft]).astype(np.float32)
    nb = nfft // 2 + 1
    Sll = np.zeros(nb, np.float64)
    Srr = np.zeros(nb, np.float64)
    Slr = np.zeros(nb, np.complex128)
    gprev = np.ones(nb)
    gmin = 10 ** (gmin_db / 20.0)
    acc = np.zeros(nfft, np.float32)
    out = []
    for i in range(0, len(xl) - nfft + 1, hop):
        L = np.fft.rfft(xl[i:i + nfft] * w)
        R = np.fft.rfft(xr[i:i + nfft] * w)
        Sll = alpha * Sll + (1 - alpha) * (L.real ** 2 + L.imag ** 2)
        Srr = alpha * Srr + (1 - alpha) * (R.real ** 2 + R.imag ** 2)
        Slr = alpha * Slr + (1 - alpha) * (L * np.conj(R))
        coh2 = (np.abs(Slr) ** 2) / np.maximum(Sll * Srr, 1e-12)
        coh2 = np.clip(coh2, 0.0, 1.0)
        # γ² = SNR/(1+SNR) → SNR = γ²/(1-γ²); Wiener gain = SNR/(1+SNR) = γ²
        g = np.sqrt(coh2)
        g = np.maximum(g, gmin)
        g[1:-1] = (g[:-2] + g[1:-1] + g[2:]) / 3.0
        a = np.where(g > gprev, 0.15, 0.65)
        g = a * gprev + (1 - a) * g
        gprev = g
        M = ((L + R) * 0.5) * g
        y = np.fft.irfft(M, nfft).astype(np.float32) * w
        acc += y
        out.append(acc[:hop].copy())
        acc = np.concatenate((acc[hop:], np.zeros(hop, np.float32)))
    return np.concatenate(out) if out else np.zeros(0, np.float32)


for a in (0.75, 0.85, 0.92):
    t0 = time.perf_counter()
    y = coherence_wiener(mix_l, mix_r, alpha=a)
    cost = (time.perf_counter() - t0) * 1000.0 / max(
        (len(mix_l) - 512) // HOP16, 1)
    eval_out(f"coherence Wiener a={a}", y, cost)

print(f"\nbest single-channel setting on the consonant band: "
      f"oversub={best[1]} floor={best[2]:.0f} dB "
      f"({best[0]:+.1f} dB mean over 2-8 kHz)")

# ── cross-check with no time alignment anywhere ──────────────────────
# Run each suppressor twice: once over the bed alone (true per-band noise
# attenuation) and once over the clean speech alone (true per-band speech
# attenuation). SNR gain = noise attenuation - speech attenuation. This
# metric cannot be corrupted by delay, so it validates the table above.
print("\nalignment-free cross-check — dB change per band, and the gain:")
print(hdr)


def two_pass(label, run_mono=None, run_dual=None):
    """dn / ds are the dB change the suppressor makes to the bed and to the
    speech, each measured against TODAY's mono-mix path (so the L+R comb is
    in the reference and cannot be charged to one candidate only).
    SNR gain = ds - dn."""
    if run_dual is not None:
        yn = run_dual(nl, nr)
        ys = run_dual(sp_l, sp_r)
    else:
        yn = run_mono(nm)
        ys = run_mono(sp_m)
    dn = 10 * np.log10(np.maximum(band_power(yn), 1e-9)
                       / np.maximum(band_power(nm), 1e-9))
    ds = 10 * np.log10(np.maximum(band_power(ys), 1e-9)
                       / np.maximum(band_power(sp_m), 1e-9))
    g = ds - dn
    print(f"  {label:28s}" + "".join(f"{v:+10.1f} " for v in g)
          + f"   300-3400 {np.mean(g[1:4]):+.1f} dB,"
            f" 2-8k {np.mean(g[3:]):+.1f} dB")
    print(f"  {'  noise kept':28s}" + "".join(f"{v:+10.1f} " for v in dn))
    print(f"  {'  speech kept':28s}" + "".join(f"{v:+10.1f} " for v in ds))
    return g


def wola_runner(oversub, fdb):
    def run(x):
        ns = au._NoiseSuppressor(MIC_NR_FRAME, oversub, fdb, MIC_NR_NOISE_S,
                                 GEMINI_SEND_RATE, smooth=MIC_NR_SMOOTH)
        out = bytearray()
        for i in range(0, len(x) - HOP16 + 1, HOP16):
            seg = np.clip(x[i:i + HOP16], -32768, 32767)
            out += ns.process(seg.astype(np.int16).tobytes())
        return np.frombuffer(bytes(out), np.int16).astype(np.float32)
    return run


two_pass("null control (must be 0.0)", run_mono=wola_identity)
for oversub in (2.0, 3.0, 3.5):
    for fdb in (-18.0, -12.0):
        two_pass(f"WOLA oversub={oversub} fl={fdb:.0f}",
                 run_mono=wola_runner(oversub, fdb))
for a in (0.85, 0.92):
    two_pass(f"coherence Wiener a={a}",
             run_dual=lambda xl, xr, a=a: coherence_wiener(xl, xr, alpha=a))
