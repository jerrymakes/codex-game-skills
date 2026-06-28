#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
from partial_alpha import color_distance, is_purple_spill


CHROMA_EDGE_DISTANCE_FAIL = 90.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate normalized partial tiles against spec."
    )
    parser.add_argument("--run-dir", help="Optional run directory with standard paths")
    parser.add_argument("--spec", help="Path to tileset_spec.json")
    parser.add_argument("--tiles-dir", help="Directory of extracted tiles")
    parser.add_argument("--output", help="Output path for QA review JSON")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
        spec_path = Path(args.spec).expanduser().resolve() if args.spec else run_dir / "tileset_spec.json"
        tiles_dir = Path(args.tiles_dir).expanduser().resolve() if args.tiles_dir else run_dir / "tiles"
        output_path = Path(args.output).expanduser().resolve() if args.output else run_dir / "qa" / "review.json"
        return spec_path, tiles_dir, output_path

    missing = [name for name, value in (("--spec", args.spec), ("--tiles-dir", args.tiles_dir), ("--output", args.output)) if not value]
    if missing:
        raise SystemExit(f"missing required arguments without --run-dir: {', '.join(missing)}")

    return (Path(args.spec).expanduser().resolve(), Path(args.tiles_dir).expanduser().resolve(), Path(args.output).expanduser().resolve())


def relpath_or_abs(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path.resolve())
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def chroma_spill_stats(img: Image.Image, key_rgb: tuple[int, int, int]) -> dict[str, int]:
    rgba = img.convert("RGBA")
    semi_transparent_count = 0
    suspicious_edge_count = 0

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = rgba.getpixel((x, y))
            if a <= 0 or a >= 255:
                continue
            semi_transparent_count += 1
            rgb = (r, g, b)
            if color_distance(rgb, key_rgb) <= CHROMA_EDGE_DISTANCE_FAIL or is_purple_spill(rgb):
                suspicious_edge_count += 1

    return {
        "semi_transparent_count": semi_transparent_count,
        "suspicious_edge_count": suspicious_edge_count,
    }


def validate_tile(obj: dict, tile_path: Path, tile_size: int, run_root: Path | None) -> dict:
    issues: list[str] = []
    img = Image.open(tile_path).convert("RGBA")
    key_hex = obj.get("chroma_key")
    if key_hex is None:
        key_rgb = (255, 0, 255)
    else:
        key_rgb = tuple(int(key_hex[i:i + 2], 16) for i in (1, 3, 5))
    expected_size = (obj["span"]["w"] * tile_size, obj["span"]["h"] * tile_size)
    if img.size != expected_size:
        issues.append(f"tile-size-mismatch:{img.size}!={expected_size}")

    alpha = img.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()
    visible_bbox = alpha.getbbox()
    if visible_bbox is None or alpha_max == 0:
        issues.append("empty-partial-tile")
    if alpha_min == 255:
        issues.append("missing-transparency")
    spill = chroma_spill_stats(img, key_rgb)
    if spill["suspicious_edge_count"] > 0:
        issues.append("chroma-spill-edge")

    return {
        "id": obj["id"],
        "label": obj["label"],
        "tile_path": relpath_or_abs(tile_path, run_root),
        "size_px": {"width": img.width, "height": img.height},
        "alpha_extrema": {"min": alpha_min, "max": alpha_max},
        "visible_bbox": None if visible_bbox is None else {
            "left": visible_bbox[0],
            "top": visible_bbox[1],
            "right": visible_bbox[2],
            "bottom": visible_bbox[3],
        },
        "chroma_spill": spill,
        "issues": issues,
    }


def main() -> None:
    args = parse_args()
    spec_path, tiles_dir, output_path = resolve_paths(args)
    run_root = Path(args.run_dir).expanduser().resolve() if args.run_dir else None
    spec = load_json(spec_path)
    if spec["sheet"]["layout_style"] != "partial":
        raise SystemExit("validate_partial_atlas.py only supports sheet.layout_style == 'partial'")

    tile_size = spec["sheet"]["tile_size"]
    chroma_key = spec["sheet"].get("chroma_key", "#FF00FF")
    review = {
        "ok": True,
        "spec_path": relpath_or_abs(spec_path, run_root),
        "summary": {"hard_failures": 0, "warnings": 0, "tile_count": len(spec["objects"])},
        "tiles": [],
    }

    for obj in spec["objects"]:
        tile_path = tiles_dir / f"{obj['id']}.png"
        if not tile_path.is_file():
            review["ok"] = False
            review["summary"]["hard_failures"] += 1
            review["tiles"].append({"id": obj["id"], "label": obj["label"], "tile_path": relpath_or_abs(tile_path, run_root), "issues": ["missing-tile"]})
            continue

        tile_review = validate_tile({**obj, "chroma_key": chroma_key}, tile_path, tile_size, run_root)
        review["tiles"].append(tile_review)
        if tile_review["issues"]:
            review["ok"] = False
            review["summary"]["hard_failures"] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
