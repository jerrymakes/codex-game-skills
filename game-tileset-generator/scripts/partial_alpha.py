#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter
from math import sqrt

from PIL import Image


def infer_chroma_key(image: Image.Image) -> tuple[int, int, int]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    samples: list[tuple[int, int, int]] = []

    for x in range(width):
        for y in (0, height - 1):
            r, g, b, a = rgba.getpixel((x, y))
            if a > 0:
                samples.append((r, g, b))

    for y in range(height):
        for x in (0, width - 1):
            r, g, b, a = rgba.getpixel((x, y))
            if a > 0:
                samples.append((r, g, b))

    if not samples:
        return (255, 0, 255)

    return Counter(samples).most_common(1)[0][0]


def remove_chroma_key(
    image: Image.Image,
    key_rgb: tuple[int, int, int] | None = None,
    transparent_threshold: float = 16.0,
    opaque_threshold: float = 54.0,
) -> Image.Image:
    rgba = image.convert("RGBA")
    key = key_rgb or infer_chroma_key(rgba)
    out = Image.new("RGBA", rgba.size)

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = rgba.getpixel((x, y))
            dist = sqrt((r - key[0]) ** 2 + (g - key[1]) ** 2 + (b - key[2]) ** 2)
            if dist <= transparent_threshold:
                alpha = 0
            elif dist >= opaque_threshold:
                alpha = a
            else:
                ratio = (dist - transparent_threshold) / (opaque_threshold - transparent_threshold)
                alpha = int(round(max(0.0, min(1.0, ratio)) * a))
            out.putpixel((x, y), (r, g, b, alpha))

    return out
