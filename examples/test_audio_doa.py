"""
test_audio_doa.py — Direction of Arrival (DOA) Algorithm Verification
==============================================================================
ADAM AI Example Suite — DGEN Technologies Pvt. Ltd.

Demonstrates and verifies the Generalized Cross-Correlation with Phase Transform
(GCC-PHAT) algorithm used by ADAM to localize human speaker direction using
two microphones separated by distance d = 65mm.
"""

import math
import numpy as np


def gcc_phat(sig_l: np.ndarray, sig_r: np.ndarray, fs: int = 48000, max_tau: float = None) -> float:
    """
    Computes Time Difference of Arrival (TDOA) in seconds using GCC-PHAT.
    """
    n = len(sig_l) + len(sig_r)
    n_fft = 2 ** int(np.ceil(np.log2(n)))

    # Compute FFT of both channels
    X1 = np.fft.rfft(sig_l, n=n_fft)
    X2 = np.fft.rfft(sig_r, n=n_fft)

    # Cross-power spectral density
    R = X1 * np.conj(X2)

    # Phase Transform (PHAT) normalization
    R_phat = R / (np.abs(R) + 1e-15)

    # Inverse FFT to get cross-correlation
    cc = np.fft.irfft(R_phat, n=n_fft)

    # Shift zero-delay to center
    max_lags = int(max_tau * fs) if max_tau else n_fft // 2
    cc = np.concatenate((cc[-max_lags:], cc[:max_lags + 1]))

    # Locate peak
    peak_index = np.argmax(np.abs(cc))
    delay_samples = peak_index - max_lags
    return float(delay_samples) / float(fs)


def calculate_doa_angle(time_delay: float, mic_distance: float = 0.065, sound_speed: float = 343.0) -> float:
    """
    Converts TDOA time delay to azimuth angle in degrees (-90 to +90).
    """
    # Clamp ratio within [-1.0, 1.0] to prevent domain errors in arcsin
    sin_theta = max(-1.0, min(1.0, (sound_speed * time_delay) / mic_distance))
    theta_rad = math.asin(sin_theta)
    return math.degrees(theta_rad)


def run_synthetic_doa_tests():
    fs = 48000
    mic_distance = 0.065   # 65 mm spacing
    sound_speed = 343.0    # Speed of sound in m/s
    max_tau = mic_distance / sound_speed

    print("=" * 65)
    print("  ADAM Acoustic Direction-of-Arrival (GCC-PHAT) Verification")
    print(f"  Microphone Baseline: {mic_distance * 1000:.1f} mm | Sample Rate: {fs} Hz")
    print("=" * 65)

    test_angles = [-60.0, -30.0, 0.0, 30.0, 60.0]

    for target_angle in test_angles:
        # Calculate theoretical time delay for target angle
        theta_rad = math.radians(target_angle)
        true_delay = (mic_distance * math.sin(theta_rad)) / sound_speed
        delay_samples = int(round(true_delay * fs))

        # Generate 0.5s band-limited noise burst simulating a human voice syllable
        t = np.linspace(0, 0.5, int(fs * 0.5), endpoint=False)
        base_signal = (
            np.sin(2 * np.pi * 300 * t) +
            0.5 * np.sin(2 * np.pi * 800 * t) +
            0.2 * np.random.normal(0, 1, len(t))
        )

        # Shift one channel by delay_samples
        if delay_samples >= 0:
            sig_l = base_signal
            sig_r = np.roll(base_signal, delay_samples)
        else:
            sig_l = np.roll(base_signal, -delay_samples)
            sig_r = base_signal

        # Run GCC-PHAT estimation
        est_delay = gcc_phat(sig_l, sig_r, fs=fs, max_tau=max_tau)
        est_angle = calculate_doa_angle(est_delay, mic_distance=mic_distance, sound_speed=sound_speed)

        error = abs(est_angle - target_angle)
        print(f"Target: {target_angle:+5.1f}°  |  Estimated: {est_angle:+5.1f}°  |  Error: {error:4.2f}°  (Delay: {est_delay*1e6:+6.1f} µs)")

    print("\nAll synthetic acoustic DOA calculations completed successfully.")


if __name__ == "__main__":
    run_synthetic_doa_tests()
