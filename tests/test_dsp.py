"""Regression tests for synthesis and FFT preview analysis."""

import unittest

import numpy as np
from PIL import Image, ImageDraw

from constants import SAMPLE_RATE
from dsp import audio_spectrogram, synthesize


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


if __name__ == "__main__":
    unittest.main()
