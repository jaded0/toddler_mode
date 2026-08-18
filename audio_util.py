#!/usr/bin/env python3
"""
Shared audio post-processing for Toddler Mode.

Every clip -- whether synthesised or downloaded from Wikimedia Commons -- goes
through the same trim/normalise path so nothing is jarringly louder, quieter or
more clipped than its neighbours.
"""

import numpy as np

SR = 24000

# Trimming. The threshold is deliberately low: quiet /s/ and /f/ onsets sit far
# below the vowel peak, and a stricter gate eats them before the vowel starts.
SILENCE_THRESH = 0.005  # fraction of peak that counts as signal
EDGE_PAD_SEC = 0.06     # silence retained either side of the signal
FADE_SEC = 0.012        # edge fade, prevents clicks

# Plosive clipping, so `b` says /b/ rather than "buh".
STOP_KEEP_SEC = 0.20
STOP_FADE_SEC = 0.070

TARGET_RMS = 0.12       # perceptual loudness match across clips
PEAK_CEILING = 0.95


def to_mono(audio):
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.flatten()


def resample(audio, src_sr, dst_sr=SR):
    """Rational resample; falls back to linear interpolation without scipy."""
    if src_sr == dst_sr:
        return audio
    try:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(src_sr), int(dst_sr))
        return resample_poly(audio, dst_sr // g, src_sr // g).astype(np.float32)
    except ImportError:
        n = int(round(len(audio) * dst_sr / src_sr))
        return np.interp(
            np.linspace(0, len(audio) - 1, n),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)


def trim_silence(audio, thresh=SILENCE_THRESH, pad=EDGE_PAD_SEC):
    """Trim leading/trailing silence based on where the signal actually is."""
    env = np.abs(audio)
    peak = env.max() if len(env) else 0.0
    if peak < 1e-6:
        return audio
    loud = np.where(env > peak * thresh)[0]
    if not len(loud):
        return audio
    start = max(0, loud[0] - int(pad * SR))
    end = min(len(audio), loud[-1] + int(pad * SR))
    return audio[start:end].copy()


def clip_plosive(audio):
    """Keep the release burst and drop the carrier vowel behind it.

    Takes the head of the already-trimmed audio rather than seeking the burst
    peak: trim_silence has positioned the start just before articulation
    begins, so this keeps the closure and any prevoicing leading into the
    burst. Seeking the peak instead made the clip start mid-burst.
    """
    end = min(len(audio), int(STOP_KEEP_SEC * SR))
    clipped = audio[:end].copy()
    fade = min(int(STOP_FADE_SEC * SR), len(clipped))
    if fade > 1:
        clipped[-fade:] *= np.linspace(1.0, 0.0, fade)
    return clipped


def polish(audio):
    """Fade the edges and normalise loudness so no key is jarringly loud."""
    audio = np.asarray(audio, dtype=np.float32).copy()
    if len(audio) < 16:
        return audio
    fade = int(FADE_SEC * SR)
    if len(audio) > 2 * fade > 2:
        audio[:fade] *= np.linspace(0.0, 1.0, fade)
        audio[-fade:] *= np.linspace(1.0, 0.0, fade)
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    if rms > 1e-6:
        audio = audio * (TARGET_RMS / rms)
    peak = float(np.max(np.abs(audio)))
    if peak > PEAK_CEILING:
        audio = audio * (PEAK_CEILING / peak)
    return audio.astype(np.float32)


def edge_energy(audio, window_sec=0.020):
    """Diagnostic: energy just inside each edge, as a fraction of peak.

    High values mean the clip starts or ends mid-sound -- i.e. content was cut.
    """
    audio = np.asarray(audio, dtype=np.float64)
    peak = np.abs(audio).max() if len(audio) else 0.0
    if peak < 1e-6 or len(audio) < 200:
        return 0.0, 0.0
    w = int(window_sec * SR)
    head = np.sqrt(np.mean(audio[:w] ** 2)) / peak
    tail = np.sqrt(np.mean(audio[-w:] ** 2)) / peak
    return float(head), float(tail)
