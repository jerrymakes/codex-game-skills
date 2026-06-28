#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROLE_ENUM = {
    "ground",
    "path",
    "liquid",
    "wall",
    "prop",
    "foliage",
    "crop",
    "structure",
}
TERRAIN_ROLE_ENUM = {"ground", "path", "liquid", "wall"}
PLACED_OBJECT_ROLE_ENUM = {"prop", "foliage", "crop", "structure"}

LAYOUT_STYLE_ENUM = {"full", "partial"}
PIXEL_MODE_ENUM = {"full", "partial"}
REPEATABILITY_ENUM = {"none", "both", "horizontal", "vertical"}
ATLAS_CONTENT_ENUM = {"terrain", "placed-object"}
LAYOUT_PRESET_ENUM = {"terrain-basic", "interior-basic"}
DEFAULT_CHROMA_KEY = "#FF00FF"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and normalize an AI-authored tileset spec."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to an AI-authored tileset spec draft",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for tileset_spec.json",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_int(data: dict, key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or value <= 0:
        raise SystemExit(f"{key} must be a positive integer")
    return value


def require_sheet(source_spec: dict) -> dict:
    sheet = source_spec.get("sheet")
    if not isinstance(sheet, dict):
        raise SystemExit("sheet must be an object")
    return sheet


def validate_top_level(source_spec: dict) -> dict:
    sheet = require_sheet(source_spec)

    layout_style = sheet.get("layout_style", sheet.get("pixel_style"))
    if layout_style not in LAYOUT_STYLE_ENUM:
        raise SystemExit("sheet.layout_style must be 'full' or 'partial'")
    sheet["layout_style"] = layout_style

    preset = sheet.get("layout_preset")
    if preset is not None and preset not in LAYOUT_PRESET_ENUM:
        raise SystemExit(f"sheet.layout_preset must be one of: {sorted(LAYOUT_PRESET_ENUM)}")

    require_int(sheet, "tile_size")
    require_int(sheet, "columns")
    require_int(sheet, "rows")

    chroma_key = sheet.get("chroma_key", DEFAULT_CHROMA_KEY)
    if not isinstance(chroma_key, str) or len(chroma_key) != 7 or not chroma_key.startswith("#"):
        raise SystemExit("sheet.chroma_key must be a hex string like '#FF00FF'")

    objects = source_spec.get("objects")
    if not isinstance(objects, list) or not objects:
        raise SystemExit("objects must be a non-empty list")

    view = sheet.get("view", "top-down")
    if not isinstance(view, str) or not view.strip():
        raise SystemExit("sheet.view must be a non-empty string")
    sheet["view"] = view.strip()

    atlas_content = sheet.get("atlas_content")
    if atlas_content is not None and atlas_content not in ATLAS_CONTENT_ENUM:
        raise SystemExit(f"sheet.atlas_content must be one of: {sorted(ATLAS_CONTENT_ENUM)}")

    return sheet


def normalize_object(obj: dict) -> dict:
    object_id = obj.get("id")
    label = obj.get("label")
    role = obj.get("role")
    pixel_mode = obj.get("pixel_mode")
    repeatability = obj.get("repeatability", "none")

    if not isinstance(object_id, str) or not object_id:
        raise SystemExit("each object.id must be a non-empty string")
    if not isinstance(label, str) or not label:
        raise SystemExit(f"object {object_id}: label must be a non-empty string")
    if role not in ROLE_ENUM:
        raise SystemExit(f"object {object_id}: role must be one of {sorted(ROLE_ENUM)}")
    if pixel_mode not in PIXEL_MODE_ENUM:
        raise SystemExit(f"object {object_id}: pixel_mode must be 'full' or 'partial'")
    if repeatability not in REPEATABILITY_ENUM:
        raise SystemExit(
            f"object {object_id}: repeatability must be one of {sorted(REPEATABILITY_ENUM)}"
        )

    span = obj.get("span", {"w": 1, "h": 1})
    if not isinstance(span, dict):
        raise SystemExit(f"object {object_id}: span must be an object")
    span_w = span.get("w", 1)
    span_h = span.get("h", 1)
    if not isinstance(span_w, int) or span_w <= 0:
        raise SystemExit(f"object {object_id}: span.w must be a positive integer")
    if not isinstance(span_h, int) or span_h <= 0:
        raise SystemExit(f"object {object_id}: span.h must be a positive integer")

    origin = obj.get("origin")
    normalized = {
        "id": object_id,
        "label": label,
        "role": role,
        "pixel_mode": pixel_mode,
        "span": {"w": span_w, "h": span_h},
        "repeatability": repeatability,
    }
    if origin is not None:
        if not isinstance(origin, dict):
            raise SystemExit(f"object {object_id}: origin must be an object")
        ox = origin.get("x")
        oy = origin.get("y")
        if not isinstance(ox, int) or ox < 0 or not isinstance(oy, int) or oy < 0:
            raise SystemExit(f"object {object_id}: origin.x and origin.y must be non-negative integers")
        normalized["origin"] = {"x": ox, "y": oy}
    return normalized


def place_objects(objects: list[dict], columns: int, rows: int) -> list[dict]:
    occupied: set[tuple[int, int]] = set()
    placed: list[dict] = []

    def can_place(origin_x: int, origin_y: int, span_w: int, span_h: int) -> bool:
        if origin_x + span_w > columns or origin_y + span_h > rows:
            return False
        for dy in range(span_h):
            for dx in range(span_w):
                if (origin_x + dx, origin_y + dy) in occupied:
                    return False
        return True

    def mark(origin_x: int, origin_y: int, span_w: int, span_h: int) -> None:
        for dy in range(span_h):
            for dx in range(span_w):
                occupied.add((origin_x + dx, origin_y + dy))

    for obj in objects:
        span_w = obj["span"]["w"]
        span_h = obj["span"]["h"]
        origin = obj.get("origin")

        if origin is None:
            placed_ok = False
            for y in range(rows):
                for x in range(columns):
                    if can_place(x, y, span_w, span_h):
                        origin = {"x": x, "y": y}
                        placed_ok = True
                        break
                if placed_ok:
                    break
            if not placed_ok:
                raise SystemExit(f"object {obj['id']}: could not find placement in sheet")
        else:
            if not can_place(origin["x"], origin["y"], span_w, span_h):
                raise SystemExit(f"object {obj['id']}: origin causes overlap or out-of-bounds placement")

        placed_obj = dict(obj)
        placed_obj["origin"] = origin
        mark(origin["x"], origin["y"], span_w, span_h)
        placed.append(placed_obj)

    return placed


def infer_atlas_content(objects: list[dict]) -> str:
    roles = {obj["role"] for obj in objects}
    if roles.issubset(TERRAIN_ROLE_ENUM):
        return "terrain"
    if roles.issubset(PLACED_OBJECT_ROLE_ENUM):
        return "placed-object"
    raise SystemExit("objects mix terrain and placed-object roles; split them into separate atlases")


def infer_layout_preset(layout_style: str) -> str:
    if layout_style == "full":
        return "terrain-basic"
    return "interior-basic"


def validate_atlas_level_conventions(sheet: dict, objects: list[dict]) -> None:
    first_pixel_mode = objects[0]["pixel_mode"]
    if any(obj["pixel_mode"] != first_pixel_mode for obj in objects):
        raise SystemExit("all objects in one atlas must use the same pixel_mode")
    if first_pixel_mode != sheet["layout_style"]:
        raise SystemExit("object pixel_mode must match sheet.layout_style for the atlas")

    first_span = objects[0]["span"]
    if any(obj["span"] != first_span for obj in objects):
        raise SystemExit("all objects in one atlas must use the same span convention")

    first_repeatability = objects[0]["repeatability"]
    if any(obj["repeatability"] != first_repeatability for obj in objects):
        raise SystemExit("all objects in one atlas must use the same repeatability convention")


def build_spec(source_spec: dict) -> dict:
    sheet = validate_top_level(source_spec)
    tile_size = require_int(sheet, "tile_size")
    columns = require_int(sheet, "columns")
    rows = require_int(sheet, "rows")

    objects = [normalize_object(obj) for obj in source_spec["objects"]]
    validate_atlas_level_conventions(sheet, objects)
    atlas_content = sheet.get("atlas_content") or infer_atlas_content(objects)
    inferred_preset = infer_layout_preset(sheet["layout_style"])
    layout_preset = sheet.get("layout_preset", inferred_preset)
    if layout_preset not in LAYOUT_PRESET_ENUM:
        raise SystemExit(f"sheet.layout_preset must be one of: {sorted(LAYOUT_PRESET_ENUM)}")
    placed_objects = place_objects(objects, columns, rows)

    return {
        "sheet": {
            "atlas_content": atlas_content,
            "view": sheet["view"],
            "layout_preset": layout_preset,
            "layout_style": sheet["layout_style"],
            "guide_outer_frame": bool(sheet.get("guide_outer_frame", False)),
            "tile_size": tile_size,
            "columns": columns,
            "rows": rows,
            "spacing": 0,
            "margin": 0,
            "background": "transparent",
            "chroma_key": sheet.get("chroma_key", DEFAULT_CHROMA_KEY),
        },
        "objects": placed_objects,
        "constraints": {
            "fixed_grid": True,
            "no_overlap": True,
            "no_out_of_bounds": True,
            "no_cross_footprint_drawing": True,
        },
        "qa": {
            "check_sheet_dimensions": True,
            "check_object_bounds": True,
            "check_empty_objects": True,
            "check_repeat_seams": True,
        },
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_spec = load_json(Path(args.input))
    spec = build_spec(source_spec)
    write_json(Path(args.output), spec)


if __name__ == "__main__":
    main()
