#!/usr/bin/env python3
"""mic_geom.py — measure the two-mic geometry and coherence on real captures.

Three things decide whether a dual-mic suppressor is the right fix, and all
three are properties of THIS hardware that have to be measured, not assumed:

  1. inter-mic delay for a real source (GCC-PHAT on /tmp/mic_C.raw)
     -> `s32_stereo_to_s16_mono_16k` sums L+R, so a nonzero delay puts a
        comb null at fs/(2D) straight into the audio.  If that lands in
        2-3.4 kHz it is eating consonants all by itself, and it moves with
        the talker's angle -- which would explain the intermittency.
  2. magnitude-squared coherence L<->R of the NOISE bed (/tmp/mic_A.raw)
     -> must be near 0 for a coherence filter to work.
  3. magnitude-squared coherence L<->R of SPEECH (/tmp/mic_C.raw)
     -> must be near 1, otherwise there is no signal for it to keep.

Also reports per-channel level match, which tells us whether one mic is
dead or much noisier than the other (in which case picking the better
single channel beats mixing).
"""
import os
import sys
import math

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CAPTURE_RATE, GEMINI_SEND_RATE
import audio_utils as au

BANDS = [(100, 300), (300, 1000), (1000, 2000), (2000, 3400),
         (3400, 5000), (5000, 8000)]


def load(path):
    s32 = np.frombuffer(open(path, "rb").read(), dtype=np.int32)
    return s32[0::2].astype(np.float64), s32[1::2].astype(np.float64)


def gcc_phat(a, b, fs, max_tau_us=600.0):
    """Delay of b relative to a, in seconds, by phase transform."""
    n = 1 << int(math.ceil(math.log2(len(a) + len(b))))
    A = np.fft.rfft(a - a.mean(), n)
    B = np.fft.rfft(b - b.mean(), n)
    R = A * np.conj(B)
    R /= np.maximum(np.abs(R), 1e-12)          # PHAT weighting
    cc = np.fft.irfft(R, n)
    lim = max(int(fs * max_tau_us * 1e-6), 1)
    cc = np.concatenate((cc[-lim:], cc[:lim + 1]))
    k = int(np.argmax(cc))
    # parabolic interpolation for sub-sample resolution (denominator is
    # negative at a maximum, so guard on magnitude, not on sign)
    d = 0.0
    if 0 < k < len(cc) - 1:
        y0, y1, y2 = cc[k - 1], cc[k], cc[k + 1]
        den = y0 - 2.0 * y1 + y2
        if abs(den) > 1e-12:
            d = float(np.clip(0.5 * (y0 - y2) / den, -1.0, 1.0))
    return ((k - lim) + d) / fs, float(cc[k] / max(np.abs(cc).max(), 1e-12))


def coherence(a, b, fs, nfft=2048):
    """Welch magnitude-squared coherence, averaged per band."""
    w = np.hanning(nfft)
    hop = nfft // 2
    Saa = np.zeros(nfft // 2 + 1)
    Sbb = np.zeros(nfft // 2 + 1)
    Sab = np.zeros(nfft // 2 + 1, dtype=complex)
    n = 0
    for i in range(0, len(a) - nfft + 1, hop):
        A = np.fft.rfft(a[i:i + nfft] * w)
        B = np.fft.rfft(b[i:i + nfft] * w)
        Saa += np.abs(A) ** 2
        Sbb += np.abs(B) ** 2
        Sab += A * np.conj(B)
        n += 1
    if not n:
        return None, None
    g2 = np.clip((np.abs(Sab) ** 2) / np.maximum(Saa * Sbb, 1e-20), 0.0, 1.0)
    frq = np.fft.rfftfreq(nfft, 1.0 / fs)
    return frq, g2


def report(label, path):
    if not os.path.exists(path):
        print(f"{label}: {path} missing — run mic_ab.py first")
        return None
    l48, r48 = load(path)
    print(f"\n{label}  ({len(l48)/CAPTURE_RATE:.1f}s)")

    rl = math.sqrt(np.mean(l48 ** 2))
    rr = math.sqrt(np.mean(r48 ** 2))
    print(f"  level  L {20*math.log10(max(rl,1)/2**31):+6.1f} dBFS   "
          f"R {20*math.log10(max(rr,1)/2**31):+6.1f} dBFS   "
          f"R-L {20*math.log10(max(rr,1)/max(rl,1)):+.1f} dB")

    tau, conf = gcc_phat(l48, r48, CAPTURE_RATE)
    d48 = tau * CAPTURE_RATE
    print(f"  GCC-PHAT delay R vs L: {tau*1e6:+.0f} us "
          f"({d48:+.2f} samples @48k, {d48*GEMINI_SEND_RATE/CAPTURE_RATE:+.2f} "
          f"@16k)  peak sharpness {conf:.2f}")
    if abs(d48) > 0.25:
        print(f"  -> L+R sum combs: first null at "
              f"{CAPTURE_RATE/(2*abs(d48)):.0f} Hz"
              + ("   *** inside the consonant band ***"
                 if 2000 <= CAPTURE_RATE / (2 * abs(d48)) <= 3400 else ""))
    else:
        print("  -> L+R sum does not comb (mics effectively co-located "
              "for this source)")

    # coherence on the 16 kHz path, i.e. after the real anti-alias + HP
    def to16(x):
        ch = au._MicChain()
        return ch.process(x.astype(np.float32)) / float(1 << au.S32_SHIFT)

    frq, g2 = coherence(to16(l48), to16(r48), GEMINI_SEND_RATE)
    print("  L<->R magnitude-squared coherence, 16 kHz path:")
    print("      " + "".join(
        f"{lo//1000 if lo>=1000 else lo}{'k' if lo>=1000 else ''}-"
        f"{hi//1000 if hi>=1000 else hi}{'k' if hi>=1000 else ''}".rjust(11)
        for lo, hi in BANDS))
    vals = [float(g2[(frq >= lo) & (frq < hi)].mean()) for lo, hi in BANDS]
    print("      " + "".join(f"{v:10.3f} " for v in vals))
    # implied SNR from gamma^2 = SNR/(1+SNR)
    print("      " + "".join(
        f"{10*math.log10(max(v,1e-6)/max(1-v,1e-6)):+10.1f} " for v in vals)
        + "  <- implied SNR (dB)")
    return vals


print(f"capture {CAPTURE_RATE} Hz, mic path -> {GEMINI_SEND_RATE} Hz")
print("A = noise bed only, C = speech through the speaker")
na = report("A  noise bed", "/tmp/mic_A.raw")
nc = report("C  speech", "/tmp/mic_C.raw")

if na and nc:
    print("\nverdict per band (C coherence - A coherence): a dual-mic "
          "coherence filter\nneeds this to be strongly positive.")
    print("      " + "".join(f"{c-a:+10.3f} " for a, c in zip(na, nc)))

# ── does each mic respond to sound at all? ───────────────────────────
# A -> C is silence -> speech.  A live mic must gain level in the speech
# bands.  A channel that does not move is not connected to the acoustic
# field, and mixing it in only adds its noise.
if os.path.exists("/tmp/mic_A.raw") and os.path.exists("/tmp/mic_C.raw"):
    print("\n── per-channel response to sound (C minus A, dB per band) ──────")
    al, ar = load("/tmp/mic_A.raw")
    cl, cr = load("/tmp/mic_C.raw")
    NF = 4096
    W = np.hanning(NF)
    F = np.fft.rfftfreq(NF, 1.0 / CAPTURE_RATE)

    def spec(x):
        acc = np.zeros(NF // 2 + 1)
        n = 0
        for i in range(0, len(x) - NF + 1, NF // 2):
            acc += np.abs(np.fft.rfft((x[i:i + NF] - x[i:i + NF].mean()) * W)) ** 2
            n += 1
        return acc / max(n, 1)

    sal, sar, scl, scr = spec(al), spec(ar), spec(cl), spec(cr)
    print("      " + "".join(
        f"{lo//1000 if lo>=1000 else lo}{'k' if lo>=1000 else ''}-"
        f"{hi//1000 if hi>=1000 else hi}{'k' if hi>=1000 else ''}".rjust(11)
        for lo, hi in BANDS))
    for nm_, a_, c_ in (("L", sal, scl), ("R", sar, scr)):
        d = [10 * math.log10(max(c_[(F >= lo) & (F < hi)].sum(), 1e-9)
                             / max(a_[(F >= lo) & (F < hi)].sum(), 1e-9))
             for lo, hi in BANDS]
        print(f"  {nm_}   " + "".join(f"{v:+10.1f} " for v in d)
              + ("   <- responds to sound" if max(d) > 6.0
                 else "   <- DEAD: does not respond to sound"))

    # What does mixing a dead channel cost?  signal halves (-6 dB) and the
    # dead channel's noise is added.
    def bp(s):
        return np.array([max(s[(F >= lo) & (F < hi)].sum(), 1e-12)
                         for lo, hi in BANDS])

    nL, nR = bp(sal), bp(sar)
    sL = np.maximum(bp(scl) - nL, 1e-12)          # speech power on L
    snr_L = 10 * np.log10(sL / nL)
    snr_mix = 10 * np.log10((sL * 0.25) / ((nL + nR) * 0.25))
    print("\n  SNR of the L channel alone vs the L+R mix that ships today:")
    print("  L only" + "".join(f"{v:+10.1f} " for v in snr_L))
    print("  L+R   " + "".join(f"{v:+10.1f} " for v in snr_mix))
    print("  cost  " + "".join(f"{a-b:+10.1f} " for a, b in
                               zip(snr_L, snr_mix))
          + "   <- dB thrown away by MIC_CHANNEL=mix")
