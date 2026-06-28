#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
from full_geometry import (
    ATLAS_ASPECT_TOLERANCE,
    CELL_ASPECT_TOLERANCE,
    check_geometry,
    fit_to_grid,
    require_acceptable_geometry,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract and normalize tiles from a full atlas candidate."
    )
    parser.add_argument("--run-dir", help="Optional run directory with standard paths")
    parser.add_argument("--spec", help="Path to tileset_spec.json")
    parser.add_argument("--input", help="Path to generated atlas candidate image")
    parser.add_argument("--tiles-dir", help="Directory for extracted tiles")
    parser.add_argument("--manifest-output", help="Output path for extraction manifest JSON")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)




def crop_object_region(image: Image.Image, fit: GridFit, origin: dict, span: dict) -> Image.Image:
    left = origin["x"] * fit.cell_width
    top = origin["y"] * fit.cell_height
    right = left + span["w"] * fit.cell_width
    bottom = top + span["h"] * fit.cell_height
    return image.crop((left, top, right, bottom))


def normalize_region(region: Image.Image, tile_size: int, span: dict) -> Image.Image:
    target_width = span["w"] * tile_size
    target_height = span["h"] * tile_size
    return region.resize((target_width, target_height), Image.Resampling.LANCZOS)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def relpath_or_abs(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path.resolve())
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
        spec_path = Path(args.spec).expanduser().resolve() if args.spec else run_dir / "tileset_spec.json"
        input_path = Path(args.input).expanduser().resolve() if args.input else run_dir / "decoded" / "atlas-candidate.png"
        tiles_dir = Path(args.tiles_dir).expanduser().resolve() if args.tiles_dir else run_dir / "tiles"
        manifest_output = Path(args.manifest_output).expanduser().resolve() if args.manifest_output else tiles_dir / "extraction-manifest.json"
        return spec_path, input_path, tiles_dir, manifest_output

    missing = [
        name
        for name, value in (
            ("--spec", args.spec),
            ("--input", args.input),
            ("--tiles-dir", args.tiles_dir),
            ("--manifest-output", args.manifest_output),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"missing required arguments without --run-dir: {', '.join(missing)}")

    return (
        Path(args.spec).expanduser().resolve(),
        Path(args.input).expanduser().resolve(),
        Path(args.tiles_dir).expanduser().resolve(),
        Path(args.manifest_output).expanduser().resolve(),
    )


def main() -> None:
    args = parse_args()
    spec_path, input_path, tiles_dir, manifest_output = resolve_paths(args)
    run_root = Path(args.run_dir).expanduser().resolve() if args.run_dir else None
    spec = load_json(spec_path)
    if spec["sheet"]["layout_style"] != "full":
        raise SystemExit("extract_full_tiles.py only supports sheet.layout_style == 'full'")

    sheet = spec["sheet"]
    tile_size = sheet["tile_size"]
    candidate = Image.open(input_path).convert("RGBA")
    fit = fit_to_grid(candidate.width, candidate.height, sheet["columns"], sheet["rows"])
    geometry = check_geometry(fit, sheet["columns"], sheet["rows"])
    require_acceptable_geometry(geometry)
    fitted = candidate.crop(fit.crop_box)

    tiles_dir.mkdir(parents=True, exist_ok=True)

    manifest_tiles: list[dict] = []

    for obj in spec["objects"]:
        region = crop_object_region(fitted, fit, obj["origin"], obj["span"])
        normalized = normalize_region(region, tile_size, obj["span"])
        tile_path = tiles_dir / f"{obj['id']}.png"
        normalized.save(tile_path)
        manifest_tiles.append(
            {
                "id": obj["id"],
                "label": obj["label"],
                "origin": obj["origin"],
                "span": obj["span"],
                "source_crop_px": {
                    "x": obj["origin"]["x"] * fit.cell_width,
                    "y": obj["origin"]["y"] * fit.cell_height,
                    "width": obj["span"]["w"] * fit.cell_width,
                    "height": obj["span"]["h"] * fit.cell_height,
                },
                "normalized_size_px": {
                    "width": normalized.width,
                    "height": normalized.height,
                },
                "output_path": relpath_or_abs(tile_path, run_root),
            }
        )

    manifest = {
        "input_path": relpath_or_abs(input_path, run_root),
        "spec_path": relpath_or_abs(spec_path, run_root),
        "candidate_size_px": {"width": candidate.width, "height": candidate.height},
        "fitted_crop_box": {
            "left": fit.crop_box[0],
            "top": fit.crop_box[1],
            "right": fit.crop_box[2],
            "bottom": fit.crop_box[3],
        },
        "geometry_check": {
            "expected_atlas_aspect": round(geometry.expected_atlas_aspect, 6),
            "actual_atlas_aspect": round(geometry.actual_atlas_aspect, 6),
            "atlas_aspect_error": round(geometry.atlas_aspect_error, 6),
            "expected_cell_aspect": round(geometry.expected_cell_aspect, 6),
            "actual_cell_aspect": round(geometry.actual_cell_aspect, 6),
            "cell_aspect_error": round(geometry.cell_aspect_error, 6),
            "atlas_aspect_tolerance": ATLAS_ASPECT_TOLERANCE,
            "cell_aspect_tolerance": CELL_ASPECT_TOLERANCE,
        },
        "fitted_grid_size_px": {"width": fit.fitted_width, "height": fit.fitted_height},
        "derived_cell_size_px": {"width": fit.cell_width, "height": fit.cell_height},
        "tiles": manifest_tiles,
    }
    write_json(manifest_output, manifest)


if __name__ == "__main__":
    main()
