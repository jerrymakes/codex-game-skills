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
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate full-atlas candidate geometry against spec before extraction."
    )
    parser.add_argument("--run-dir", help="Optional run directory with standard paths")
    parser.add_argument("--spec", help="Path to tileset_spec.json")
    parser.add_argument("--input", help="Path to decoded atlas candidate image")
    parser.add_argument("--output", help="Output path for candidate QA JSON")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
        spec_path = Path(args.spec).expanduser().resolve() if args.spec else run_dir / "tileset_spec.json"
        input_path = Path(args.input).expanduser().resolve() if args.input else run_dir / "decoded" / "atlas-candidate.png"
        output_path = Path(args.output).expanduser().resolve() if args.output else run_dir / "qa" / "candidate-review.json"
        return spec_path, input_path, output_path

    missing = [
        name
        for name, value in (
            ("--spec", args.spec),
            ("--input", args.input),
            ("--output", args.output),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"missing required arguments without --run-dir: {', '.join(missing)}")

    return (
        Path(args.spec).expanduser().resolve(),
        Path(args.input).expanduser().resolve(),
        Path(args.output).expanduser().resolve(),
    )


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


def main() -> None:
    args = parse_args()
    spec_path, input_path, output_path = resolve_paths(args)
    run_root = Path(args.run_dir).expanduser().resolve() if args.run_dir else None
    spec = load_json(spec_path)
    if spec["sheet"]["layout_style"] != "full":
        raise SystemExit("validate_full_candidate.py only supports sheet.layout_style == 'full'")

    sheet = spec["sheet"]
    with Image.open(input_path) as image:
        width, height = image.size

    fit = fit_to_grid(width, height, sheet["columns"], sheet["rows"])
    geometry = check_geometry(fit, sheet["columns"], sheet["rows"])

    issues: list[str] = []
    if geometry.atlas_aspect_error > ATLAS_ASPECT_TOLERANCE:
        issues.append("atlas-aspect-mismatch")
    if geometry.cell_aspect_error > CELL_ASPECT_TOLERANCE:
        issues.append("cell-aspect-mismatch")

    review = {
        "ok": not issues,
        "spec_path": relpath_or_abs(spec_path, run_root),
        "input_path": relpath_or_abs(input_path, run_root),
        "candidate_size_px": {"width": width, "height": height},
        "fitted_crop_box": {
            "left": fit.crop_box[0],
            "top": fit.crop_box[1],
            "right": fit.crop_box[2],
            "bottom": fit.crop_box[3],
        },
        "fitted_grid_size_px": {"width": fit.fitted_width, "height": fit.fitted_height},
        "derived_cell_size_px": {"width": fit.cell_width, "height": fit.cell_height},
        "geometry": {
            "expected_atlas_aspect": round(geometry.expected_atlas_aspect, 6),
            "actual_atlas_aspect": round(geometry.actual_atlas_aspect, 6),
            "atlas_aspect_error": round(geometry.atlas_aspect_error, 6),
            "expected_cell_aspect": round(geometry.expected_cell_aspect, 6),
            "actual_cell_aspect": round(geometry.actual_cell_aspect, 6),
            "cell_aspect_error": round(geometry.cell_aspect_error, 6),
            "atlas_aspect_tolerance": ATLAS_ASPECT_TOLERANCE,
            "cell_aspect_tolerance": CELL_ASPECT_TOLERANCE,
        },
        "issues": issues,
    }
    write_json(output_path, review)


if __name__ == "__main__":
    main()
