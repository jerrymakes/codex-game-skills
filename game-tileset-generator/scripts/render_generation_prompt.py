#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROLE_HINTS = {
    "ground": "continuous ground surface",
    "path": "walkable path surface",
    "liquid": "liquid surface",
    "wall": "wall block surface",
    "prop": "small environmental prop",
    "foliage": "foliage or plant element",
    "crop": "plant element",
    "structure": "structural built element",
}
REPEATABILITY_HINTS = {
    "none": "non-repeatable",
    "both": "repeatable seamless tiling in both directions",
    "horizontal": "repeatable seamless tiling horizontally",
    "vertical": "repeatable seamless tiling vertically",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render atlas generation prompts from a tileset spec."
    )
    parser.add_argument("--spec", required=True, help="Path to tileset_spec.json")
    parser.add_argument(
        "--prompt-output", required=True, help="Output path for generation_prompt.txt"
    )
    parser.add_argument(
        "--negative-output",
        required=True,
        help="Output path for prompt-negative.txt",
    )
    return parser.parse_args()


def load_spec(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def object_sort_key(obj: dict) -> tuple[int, int, str]:
    return (obj["origin"]["y"], obj["origin"]["x"], obj["id"])


def validate_spec(spec: dict) -> str:
    layout_style = spec["sheet"].get("layout_style", "full")
    if layout_style not in {"full", "partial"}:
        raise SystemExit("sheet.layout_style must be 'full' or 'partial'")
    return layout_style


def build_positive_prompt(spec: dict, layout_style: str) -> str:
    sheet = spec["sheet"]
    objects = sorted(spec["objects"], key=object_sort_key)
    chroma_key = sheet.get("chroma_key", "#FF00FF")
    view = sheet.get("view", "top-down")
    atlas_content = sheet.get("atlas_content")

    header = [
        "Generate one game tileset atlas as a single structured sheet.",
        f"Atlas pixel style: {layout_style}.",
        f"Gameplay view: {view}.",
        (
            f"Use a {sheet['columns']} by {sheet['rows']} grid with "
            f"{sheet['tile_size']}x{sheet['tile_size']} logical tiles."
        ),
        (
            f"The whole atlas must read as a {sheet['columns']} by {sheet['rows']} sheet of square cells, "
            "with a wide landscape aspect ratio that matches the grid."
        ),
        "Do not generate a square canvas, portrait canvas, or vertically stretched tile sheet for this atlas.",
        "Do not copy any rounded frame or decorative outer border from the layout guide.",
        "Treat this as an engine-facing tileset atlas, not a showcase image or presentation board.",
        "Keep every object inside its assigned footprint.",
        "Do not add labels, text, UI, borders, guide marks, or extra cells.",
        "",
        "Atlas objects in reading order:",
    ]

    if atlas_content:
        header.insert(3, f"Atlas content type: {atlas_content}.")

    if layout_style == "partial":
        header.insert(4, f"Use a perfectly flat solid {chroma_key} chroma-key background around and between objects where transparency is required.")
        header.insert(5, f"Do not use {chroma_key} inside the artwork itself.")
        header.insert(6, "Do not tint anti-aliased edges, semi-transparent edge pixels, or contact shadows with the chroma-key color.")
        header.insert(7, "Keep object edge colors neutral or true to the material, not magenta-fringed.")
        header.insert(10, "Keep each object smaller than the full tile area so empty transparent space remains around it.")
        header.insert(11, "Do not make partial objects fill the entire tile cell edge-to-edge.")
    else:
        header.insert(4, "Use a transparent background outside the rectangular atlas only.")
        header.insert(10, "Fill each full tile cell edge-to-edge with tile artwork.")
        header.insert(11, "Do not leave gutters, padding bands, empty borders, or framing space between neighboring cells.")

    object_lines = []
    for obj in objects:
        span = obj["span"]
        origin = obj["origin"]
        role_hint = ROLE_HINTS.get(obj["role"], obj["role"])
        repeatability = obj.get("repeatability", "both" if obj.get("repeatable") else "none")
        repeat_note = REPEATABILITY_HINTS[repeatability]
        object_lines.append(
            (
                f"- {obj['id']}: {obj['label']}, role {obj['role']} ({role_hint}), "
                f"footprint {span['w']}x{span['h']} tile(s), "
                f"origin ({origin['x']}, {origin['y']}), "
                f"pixel mode {obj['pixel_mode']}, {repeat_note}."
            )
        )

    footer = [
        "",
        "Preserve clean grid alignment across the whole atlas.",
    ]

    if any(obj.get("repeatability", "both" if obj.get("repeatable") else "none") != "none" for obj in objects):
        footer.append(
            "Objects marked repeatable should read as seamless when tiled adjacent to copies of themselves in their declared repeatability directions."
        )
        footer.append(
            "For repeatable full tiles, paint through the relevant repeatability edges cleanly."
        )

    if any(obj["span"]["w"] > 1 or obj["span"]["h"] > 1 for obj in objects):
        footer.append(
            "Multi-tile objects must read as one coherent object across their full footprint."
        )

    return "\n".join(header + object_lines + footer).strip() + "\n"


def build_negative_prompt(layout_style: str) -> str:
    if layout_style == "full":
        lines = [
            "Do not draw isolated tiny props floating in cells intended as full surfaces.",
            "Do not leave large transparent margins inside cells.",
            "Do not shrink artwork into partial occupancy behavior.",
            "Do not break edge continuity on repeatable surfaces.",
            "Do not spill artwork outside assigned cell or footprint boundaries.",
            "Do not introduce visible gutters, padding bands, frame lines, or empty border strips between tiles.",
            "Do not present the atlas as a mockup, poster, card sheet, or gallery board.",
            "Do not add text, labels, grid marks, shadows outside cells, extra decoration, or any rounded outer frame.",
        ]
    else:
        lines = [
            "Do not let artwork touch or cross outside the intended safe area.",
            "Do not make small-object cells read like full-cell filled surfaces unless explicitly intended.",
            "Do not spill artwork into neighboring cells or outside the assigned footprint.",
            "Do not remove the transparent space needed around smaller objects.",
            "Do not leave magenta fringe, purple spill, or chroma-key contamination on semi-transparent edges.",
            "Do not anti-alias object edges against the chroma-key background color.",
            "Do not add text, labels, grid marks, shadows outside cells, extra decoration, or any rounded outer frame.",
            "Do not merge separate objects into one continuous filled sheet.",
        ]
    return "\n".join(lines).strip() + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    spec = load_spec(Path(args.spec))
    layout_style = validate_spec(spec)
    positive = build_positive_prompt(spec, layout_style)
    negative = build_negative_prompt(layout_style)
    write_text(Path(args.prompt_output), positive)
    write_text(Path(args.negative_output), negative)


if __name__ == "__main__":
    main()
