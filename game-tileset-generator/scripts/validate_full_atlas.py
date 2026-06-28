#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


SEAM_DIFF_WARN = 28.0
SEAM_DIFF_FAIL = 48.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate normalized full tiles against spec."
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

    missing = [
        name
        for name, value in (
            ("--spec", args.spec),
            ("--tiles-dir", args.tiles_dir),
            ("--output", args.output),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"missing required arguments without --run-dir: {', '.join(missing)}")

    return (
        Path(args.spec).expanduser().resolve(),
        Path(args.tiles_dir).expanduser().resolve(),
        Path(args.output).expanduser().resolve(),
    )


def mean_abs_diff(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / len(stat.mean)


def edge_pair_diffs(tile: Image.Image) -> dict[str, float]:
    rgba = tile.convert("RGBA")
    left = rgba.crop((0, 0, 1, rgba.height))
    right = rgba.crop((rgba.width - 1, 0, rgba.width, rgba.height))
    top = rgba.crop((0, 0, rgba.width, 1))
    bottom = rgba.crop((0, rgba.height - 1, rgba.width, rgba.height))
    return {
        "left_right": mean_abs_diff(left, right),
        "top_bottom": mean_abs_diff(top, bottom),
    }


def seam_checks_for_repeatability(repeatability: str) -> list[str]:
    if repeatability == "both":
        return ["left_right", "top_bottom"]
    if repeatability == "horizontal":
        return ["left_right"]
    if repeatability == "vertical":
        return ["top_bottom"]
    return []


def relpath_or_abs(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path.resolve())
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def validate_tile(obj: dict, tile_path: Path, tile_size: int, run_root: Path | None) -> dict:
    issues: list[str] = []
    img = Image.open(tile_path).convert("RGBA")
    expected_size = (obj["span"]["w"] * tile_size, obj["span"]["h"] * tile_size)
    if img.size != expected_size:
        issues.append(f"tile-size-mismatch:{img.size}!={expected_size}")

    alpha = img.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min < 255:
        issues.append("unexpected-transparency")

    seam = edge_pair_diffs(img)
    seam_status = "ok"
    seam_issues: list[str] = []
    repeatability = obj.get("repeatability", "both" if obj.get("repeatable") else "none")
    seam_checks = seam_checks_for_repeatability(repeatability)
    if seam_checks:
        worst = max(seam[name] for name in seam_checks)
        if worst >= SEAM_DIFF_FAIL:
            seam_status = "fail"
            seam_issues.append("repeat-seam-fail")
        elif worst >= SEAM_DIFF_WARN:
            seam_status = "warn"
            seam_issues.append("repeat-seam-warn")

    issues.extend(seam_issues)
    return {
        "id": obj["id"],
        "label": obj["label"],
        "tile_path": relpath_or_abs(tile_path, run_root),
        "size_px": {"width": img.width, "height": img.height},
        "alpha_extrema": {"min": alpha_min, "max": alpha_max},
        "repeatable": obj.get("repeatable", False),
        "repeatability": repeatability,
        "seam_checks": seam_checks,
        "seam_diff": seam,
        "seam_status": seam_status,
        "issues": issues,
    }


def main() -> None:
    args = parse_args()
    spec_path, tiles_dir, output_path = resolve_paths(args)
    run_root = Path(args.run_dir).expanduser().resolve() if args.run_dir else None
    spec = load_json(spec_path)
    if spec["sheet"]["layout_style"] != "full":
        raise SystemExit("validate_full_atlas.py only supports sheet.layout_style == 'full'")

    tile_size = spec["sheet"]["tile_size"]

    review: dict = {
        "ok": True,
        "spec_path": relpath_or_abs(spec_path, run_root),
        "summary": {
            "hard_failures": 0,
            "warnings": 0,
            "tile_count": len(spec["objects"]),
        },
        "tiles": [],
    }

    for obj in spec["objects"]:
        tile_path = tiles_dir / f"{obj['id']}.png"
        if not tile_path.is_file():
            review["ok"] = False
            review["summary"]["hard_failures"] += 1
            review["tiles"].append(
                {
                    "id": obj["id"],
                    "label": obj["label"],
                    "tile_path": relpath_or_abs(tile_path, run_root),
                    "issues": ["missing-tile"],
                }
            )
            continue

        tile_review = validate_tile(obj, tile_path, tile_size, run_root)
        review["tiles"].append(tile_review)
        if any(issue not in {"repeat-seam-warn"} for issue in tile_review["issues"]):
            review["ok"] = False
            review["summary"]["hard_failures"] += 1
        elif tile_review["issues"]:
            review["summary"]["warnings"] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
