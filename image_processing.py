"""Image orientation, cleanup, and simulated channel-resolution processing."""

import numpy as np
from PIL import Image, ImageOps

from constants import ORIENTATIONS


def rotate_for_transmission(image: Image.Image, orientation: str) -> Image.Image:
    if orientation in (ORIENTATIONS[0], ORIENTATIONS[2]):
        return image.transpose(Image.Transpose.ROTATE_270)
    if orientation == ORIENTATIONS[1]:
        return image.transpose(Image.Transpose.ROTATE_90)
    if orientation == ORIENTATIONS[3]:
        return image.transpose(Image.Transpose.ROTATE_180)
    return image.copy()


def predicted_waterfall(transmit_image: Image.Image, orientation: str) -> Image.Image:
    """Convert time-horizontal synthesis artwork to a conventional RF view."""
    if orientation in (ORIENTATIONS[0], ORIENTATIONS[2]):
        return ImageOps.flip(transmit_image.transpose(Image.Transpose.ROTATE_90))
    if orientation == ORIENTATIONS[1]:
        return transmit_image.transpose(Image.Transpose.ROTATE_270)
    if orientation == ORIENTATIONS[3]:
        return transmit_image.transpose(Image.Transpose.ROTATE_180)
    return transmit_image.transpose(Image.Transpose.ROTATE_270)


def channel_image(image: Image.Image, rows: int, threshold: int,
                  gamma: float, thicken: int) -> Image.Image:
    """Reduce artwork to the frequency detail the selected channel can resolve."""
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    gray = np.where(gray * 255 >= threshold, gray, 0.0)
    gray = np.power(gray, gamma)
    processed = Image.fromarray(np.uint8(np.clip(gray, 0, 1) * 255), "L")
    target_h = max(16, rows)
    target_w = max(8, round(processed.width * target_h / max(1, processed.height)))
    processed = processed.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if thicken:
        from PIL import ImageFilter
        processed = processed.filter(ImageFilter.MaxFilter(thicken * 2 + 1))
    return processed


def trim_glyph_time_margins(image: Image.Image, threshold: int, horizontal: bool = False) -> Image.Image:
    """Remove font whitespace that becomes dead time after rotation."""
    pixels = np.asarray(image.convert("L"))
    if horizontal:
        occupied = np.any(pixels >= max(1, threshold), axis=0)
        indices = np.flatnonzero(occupied)
        if not indices.size: return image
        return image.crop((int(indices[0]), 0, int(indices[-1]) + 1, image.height))
    else:
        occupied = np.any(pixels >= max(1, threshold), axis=1)
        indices = np.flatnonzero(occupied)
        if not indices.size: return image
        return image.crop((0, int(indices[0]), image.width, int(indices[-1]) + 1))


def glyph_duration(base_seconds: float, glyph_height: int,
                   reference_height: int) -> float:
    """Scale airtime to printed glyph height without zero-length marks."""
    scale = min(1.25, max(.08, glyph_height / max(1, reference_height)))
    return max(.08, base_seconds * scale)


def expand_preset_art(image: Image.Image, canvas=(360, 120),
                      margin=(14, 7)) -> Image.Image:
    """Crop preset dead space and expand its ink across the usable RF canvas."""
    gray = image.convert("L")
    bbox = gray.getbbox()
    if not bbox:
        return Image.new("L", canvas, 0)
    target = (max(1, canvas[0] - 2 * margin[0]),
              max(1, canvas[1] - 2 * margin[1]))
    ink = gray.crop(bbox).resize(target, Image.Resampling.NEAREST)
    result = Image.new("L", canvas, 0)
    result.paste(ink, margin)
    return result
