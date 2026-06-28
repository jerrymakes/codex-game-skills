#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a visual layout guide from a tileset spec."
    )
    parser.add_argument("--spec", required=True, help="Path to tileset_spec.json")
    parser.add_argument("--output", required=True, help="Output PNG path")
    parser.add_argument(
        "--cell-px",
        type=int,
        default=112,
        help="Preview pixel size used to render each logical tile cell",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=0,
        help="Outer canvas padding around the atlas preview",
    )
    return parser.parse_args()


def load_spec(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def draw_grid(draw: ImageDraw.ImageDraw, left: int, top: int, cols: int, rows: int, cell: int) -> None:
    draw_grid_with_options(draw, left, top, cols, rows, cell, outer_frame=True)


def draw_grid_with_options(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    cols: int,
    rows: int,
    cell: int,
    outer_frame: bool,
) -> None:
    width = cols * cell
    height = rows * cell
    fill = (247, 247, 247, 255)
    if outer_frame:
        radius = max(12, cell // 4)
        draw.rounded_rectangle(
            (left, top, left + width, top + height),
            radius=radius,
            fill=fill,
            outline=(48, 48, 48, 255),
            width=2,
        )
    else:
        draw.rectangle((left, top, left + width, top + height), fill=fill)

    for col in range(1, cols):
        x = left + col * cell
        draw.line((x, top, x, top + height), fill=(48, 48, 48, 255), width=2)

    for row in range(1, rows):
        y = top + row * cell
        draw.line((left, y, left + width, y), fill=(48, 48, 48, 255), width=2)


def draw_partial_hints(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    width: int,
    height: int,
    cell: int,
) -> None:
    inset = max(10, cell // 8)
    guide_color = (143, 192, 255, 255)
    cross_color = (210, 210, 210, 255)

    draw.rectangle(
        (left + inset, top + inset, left + width - inset, top + height - inset),
        outline=guide_color,
        width=2,
    )

    cx = left + width / 2
    cy = top + height / 2
    dash = max(6, cell // 12)

    draw_dashed_line(draw, (left + inset, cy), (left + width - inset, cy), dash, cross_color)
    draw_dashed_line(draw, (cx, top + inset), (cx, top + height - inset), dash, cross_color)


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    dash: int,
    color: tuple[int, int, int, int],
) -> None:
    x1, y1 = start
    x2, y2 = end

    if x1 == x2:
        y = y1
        while y < y2:
            draw.line((x1, y, x1, min(y + dash, y2)), fill=color, width=1)
            y += dash * 2
        return

    x = x1
    while x < x2:
        draw.line((x, y1, min(x + dash, x2), y1), fill=color, width=1)
        x += dash * 2


def validate_objects(spec: dict) -> None:
    sheet = spec["sheet"]
    cols = sheet["columns"]
    rows = sheet["rows"]
    occupied: set[tuple[int, int]] = set()

    for obj in spec["objects"]:
        ox = obj["origin"]["x"]
        oy = obj["origin"]["y"]
        sw = obj["span"]["w"]
        sh = obj["span"]["h"]

        if ox < 0 or oy < 0 or ox + sw > cols or oy + sh > rows:
            raise SystemExit(f"object {obj['id']} is out of bounds")

        for dy in range(sh):
            for dx in range(sw):
                key = (ox + dx, oy + dy)
                if key in occupied:
                    raise SystemExit(f"object {obj['id']} overlaps tile {key}")
                occupied.add(key)


def render(spec: dict, output_path: Path, cell_px: int, padding: int) -> None:
    sheet = spec["sheet"]
    cols = sheet["columns"]
    rows = sheet["rows"]
    layout_style = sheet.get("layout_style", "full")
    guide_outer_frame = bool(sheet.get("guide_outer_frame", False))
    if layout_style not in {"full", "partial"}:
        raise SystemExit("sheet.layout_style must be 'full' or 'partial'")
    atlas_w = cols * cell_px
    atlas_h = rows * cell_px
    width = atlas_w + padding * 2
    height = atlas_h + padding * 2

    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    left = padding
    top = padding

    draw_grid_with_options(draw, left, top, cols, rows, cell_px, guide_outer_frame)

    for obj in spec["objects"]:
        ox = obj["origin"]["x"]
        oy = obj["origin"]["y"]
        sw = obj["span"]["w"]
        sh = obj["span"]["h"]

        box_left = left + ox * cell_px
        box_top = top + oy * cell_px
        box_width = sw * cell_px
        box_height = sh * cell_px

        if layout_style == "partial":
            draw_partial_hints(draw, box_left, box_top, box_width, box_height, cell_px)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec)
    output_path = Path(args.output)
    spec = load_spec(spec_path)
    validate_objects(spec)
    render(spec, output_path, args.cell_px, args.padding)


if __name__ == "__main__":
    main()
