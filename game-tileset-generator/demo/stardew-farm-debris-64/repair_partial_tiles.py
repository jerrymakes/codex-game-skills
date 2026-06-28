#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


KEY_RGB = (255, 0, 255)


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    dr = a[0] - b[0]
    dg = a[1] - b[1]
    db = a[2] - b[2]
    return (dr * dr + dg * dg + db * db) ** 0.5


def is_suspicious(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return color_distance(rgb, KEY_RGB) <= 90 or (
        max(r, b) >= 120 and g <= 110 and abs(r - b) <= 95 and (r + b) - (2 * g) >= 80
    )


def repair_image(path: Path) -> tuple[int, int]:
    image = Image.open(path).convert("RGBA")
    repaired = 0
    semi = 0

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = image.getpixel((x, y))
            if 0 < a < 255:
                semi += 1
                if is_suspicious((r, g, b)):
                    image.putpixel((x, y), (0, 0, 0, 0))
                    repaired += 1

    image.save(path)
    return semi, repaired


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove magenta fringe from extracted partial tiles.")
    parser.add_argument("--tiles-dir", required=True)
    args = parser.parse_args()

    tiles_dir = Path(args.tiles_dir).resolve()
    for path in sorted(tiles_dir.glob("*.png")):
        semi, repaired = repair_image(path)
        print(f"{path.name}: semi={semi} repaired={repaired}")


if __name__ == "__main__":
    main()
