#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter
from math import sqrt

from PIL import Image


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def is_purple_spill(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return (
        max(r, b) >= 120
        and g <= 110
        and abs(r - b) <= 95
        and (r + b) - (2 * g) >= 80
    )


def decontaminate_rgb(
    rgb: tuple[int, int, int],
    key: tuple[int, int, int],
    alpha: int,
) -> tuple[int, int, int]:
    if alpha <= 0:
        return (0, 0, 0)
    if alpha >= 255:
        return rgb

    a = alpha / 255.0
    cleaned = []
    for channel, key_channel in zip(rgb, key):
        value = (channel - key_channel * (1.0 - a)) / a
        cleaned.append(int(round(max(0.0, min(255.0, value)))))
    return (cleaned[0], cleaned[1], cleaned[2])


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
    transparent_threshold: float = 24.0,
    opaque_threshold: float = 110.0,
    spill_threshold: float = 170.0,
    min_visible_alpha: int = 32,
) -> Image.Image:
    rgba = image.convert("RGBA")
    key = key_rgb or infer_chroma_key(rgba)
    out = Image.new("RGBA", rgba.size)

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = rgba.getpixel((x, y))
            rgb = (r, g, b)
            dist = color_distance(rgb, key)
            if dist <= transparent_threshold:
                alpha = 0
            elif dist <= opaque_threshold:
                ratio = (dist - transparent_threshold) / (opaque_threshold - transparent_threshold)
                alpha = int(round(max(0.0, min(1.0, ratio)) * a))
            elif dist <= spill_threshold:
                ratio = (dist - opaque_threshold) / (spill_threshold - opaque_threshold)
                spill_alpha = 0.4 + 0.6 * max(0.0, min(1.0, ratio))
                alpha = int(round(spill_alpha * a))
            else:
                alpha = a

            if alpha <= min_visible_alpha:
                alpha = 0

            if is_purple_spill(rgb) and alpha <= 96:
                alpha = 0

            cleaned_rgb = decontaminate_rgb(rgb, key, alpha)
            out.putpixel((x, y), (cleaned_rgb[0], cleaned_rgb[1], cleaned_rgb[2], alpha))

    return out
