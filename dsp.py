"""Waterfall audio synthesis, analysis, and VOX helper functions."""

import numpy as np
from PIL import Image

from constants import SAMPLE_RATE


def activity_level_dbfs(samples: np.ndarray, block_samples=4800) -> float:
    """Return 90th-percentile block RMS, ignoring isolated HF noise pops."""
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not values.size:
        return -120.0
    levels = []
    for start in range(0, len(values), max(1, block_samples)):
        block = values[start:start + block_samples]
        levels.append(float(np.sqrt(np.mean(np.square(block), dtype=np.float64))))
    return 20.0 * np.log10(max(1e-6, float(np.percentile(levels, 90))))


def synthesize(image: Image.Image, low_hz: float, high_hz: float,
               duration: float, level: float) -> np.ndarray:
    """Create phase-continuous multitone audio from a monochrome raster."""
    pixels = np.flipud(np.asarray(image.convert("L"), dtype=np.float32) / 255.0)
    rows, columns = pixels.shape
    samples_per_column = max(96, int(SAMPLE_RATE * duration / max(1, columns)))
    frequencies = np.linspace(low_hz, high_hz, rows, dtype=np.float64)
    omega = 2 * np.pi * frequencies / SAMPLE_RATE
    phase = np.zeros(rows, dtype=np.float64)
    n = np.arange(samples_per_column, dtype=np.float64)
    ramp = np.linspace(0, 1, samples_per_column, endpoint=False, dtype=np.float32)
    previous = np.zeros(rows, dtype=np.float32)
    pieces = []
    for column in range(columns):
        current = pixels[:, column]
        active = np.maximum(previous, current) > .025
        if not np.any(active):
            block = np.zeros(samples_per_column, dtype=np.float32)
        else:
            amplitudes = previous[active, None] + (
                current[active, None] - previous[active, None]) * ramp[None, :]
            tones = np.sin(phase[active, None] + omega[active, None] * n)
            block = np.sum(amplitudes * tones, axis=0)
            block = (block / max(1.0, np.sqrt(float(active.sum())) * 1.65)).astype(np.float32)
        phase = (phase + omega * samples_per_column) % (2 * np.pi)
        previous = current
        pieces.append(block)
    audio = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
    edge = min(480, len(audio) // 4)
    if edge:
        audio[:edge] *= np.linspace(0, 1, edge, dtype=np.float32)
        audio[-edge:] *= np.linspace(1, 0, edge, dtype=np.float32)
    peak = float(np.max(np.abs(audio)))
    return (audio / peak * level if peak else audio).astype(np.float32)


def add_vox_guards(audio: np.ndarray, seconds: float, frequency: float,
                   amplitude: float) -> np.ndarray:
    """Surround picture audio with tones that let VOX key and settle."""
    count = round(SAMPLE_RATE * seconds)
    if count <= 0:
        return audio
    n = np.arange(count, dtype=np.float64)
    guard = (np.sin(2*np.pi*frequency*n/SAMPLE_RATE) * amplitude).astype(np.float32)
    edge = min(240, count // 4)
    if edge:
        guard[:edge] *= np.linspace(0, 1, edge, dtype=np.float32)
        guard[-edge:] *= np.linspace(1, 0, edge, dtype=np.float32)
    settle = np.zeros(round(SAMPLE_RATE * .12), dtype=np.float32)
    return np.concatenate((guard, settle, audio, guard))


def audio_spectrogram(audio: np.ndarray, low_hz: float, high_hz: float,
                      fft_size=4096, hop=1024) -> Image.Image:
    """Analyze generated audio into a time-down, frequency-right waterfall."""
    values = np.asarray(audio, dtype=np.float32).reshape(-1)
    if len(values) < fft_size:
        values = np.pad(values, (0, fft_size - len(values)))
    window = np.hanning(fft_size).astype(np.float32)
    spectra = []
    for start in range(0, len(values) - fft_size + 1, hop):
        power = np.abs(np.fft.rfft(values[start:start+fft_size] * window))
        spectra.append(20 * np.log10(np.maximum(power, 1e-7)))
    matrix = np.asarray(spectra, dtype=np.float32)
    freqs = np.fft.rfftfreq(fft_size, 1 / SAMPLE_RATE)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    matrix = matrix[:, mask]
    if not matrix.size:
        return Image.new("L", (320, 2), 0)
    floor = float(np.percentile(matrix, 25))
    ceiling = float(np.percentile(matrix, 99.7))
    normalized = np.clip((matrix - floor) / max(1e-6, ceiling-floor), 0, 1)
    return Image.fromarray(np.uint8(normalized * 255), "L")
