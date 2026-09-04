"""Regression tests for geometry and channel-image helpers."""

import unittest

from PIL import Image, ImageDraw

from image_processing import expand_preset_art, glyph_duration, trim_glyph_time_margins


class ImageProcessingTests(unittest.TestCase):
    def test_trim_only_time_axis(self):
        image = Image.new("L", (120, 120), 0)
        ImageDraw.Draw(image).rectangle((20, 31, 99, 87), fill=255)
        self.assertEqual(trim_glyph_time_margins(image, 35).size, (120, 57))

    def test_small_punctuation_gets_shorter_airtime(self):
        self.assertEqual(glyph_duration(5, 55, 55), 5)
        self.assertLess(glyph_duration(5, 6, 55), .6)

    def test_preset_fills_canvas(self):
        image = Image.new("L", (360, 120), 0)
        ImageDraw.Draw(image).ellipse((126, 8, 234, 112), fill=255)
        result = expand_preset_art(image)
        self.assertEqual(result.size, (360, 120))
        self.assertEqual(result.getbbox(), (14, 7, 346, 113))


if __name__ == "__main__":
    unittest.main()
