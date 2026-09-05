"""Regression tests for synthesis and FFT preview analysis."""

import unittest

import numpy as np
from PIL import Image, ImageDraw

from constants import SAMPLE_RATE
from dsp import audio_spectrogram, morse_id, synthesize


class DspTests(unittest.TestCase):
    def test_synthesis_duration(self):
        image = Image.new("L", (20, 16), 0)
        ImageDraw.Draw(image).line((0, 8, 19, 8), fill=255)
        audio = synthesize(image, 500, 2500, 1.0, .2)
        self.assertAlmostEqual(len(audio) / SAMPLE_RATE, 1.0, places=2)
        self.assertLessEqual(float(np.max(np.abs(audio))), .201)

    def test_fft_finds_center_tone(self):
        n = np.arange(SAMPLE_RATE, dtype=np.float32)
        audio = np.sin(2*np.pi*1000*n/SAMPLE_RATE).astype(np.float32)
        image = audio_spectrogram(audio, 500, 1500)
        spectrum = np.asarray(image, dtype=np.float32).mean(axis=0)
        peak_fraction = int(np.argmax(spectrum)) / max(1, len(spectrum)-1)
        self.assertAlmostEqual(peak_fraction, .5, delta=.08)

    def test_morse_id_has_standard_relative_timing(self):
        # E is one dot, T is one dash, with a three-dot character gap.
        audio = morse_id("ET", frequency=700, wpm=20, level=.2)
        dot_samples = round(SAMPLE_RATE * 1.2 / 20)
        self.assertEqual(len(audio), dot_samples * 7)
        self.assertLessEqual(float(np.max(np.abs(audio))), .201)


if __name__ == "__main__":
    unittest.main()
