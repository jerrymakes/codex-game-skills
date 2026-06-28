#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose a final normalized full atlas from extracted tiles."
    )
    parser.add_argument("--run-dir", help="Optional run directory with standard paths")
    parser.add_argument("--spec", help="Path to tileset_spec.json")
    parser.add_argument("--tiles-dir", help="Directory of extracted tiles")
    parser.add_argument("--output", help="Output path for final atlas PNG")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
        spec_path = Path(args.spec).expanduser().resolve() if args.spec else run_dir / "tileset_spec.json"
        tiles_dir = Path(args.tiles_dir).expanduser().resolve() if args.tiles_dir else run_dir / "tiles"
        output_path = Path(args.output).expanduser().resolve() if args.output else run_dir / "final" / "atlas.png"
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


def main() -> None:
    args = parse_args()
    spec_path, tiles_dir, output_path = resolve_paths(args)
    spec = load_json(spec_path)
    if spec["sheet"]["layout_style"] != "full":
        raise SystemExit("compose_full_atlas.py only supports sheet.layout_style == 'full'")

    sheet = spec["sheet"]
    tile_size = sheet["tile_size"]
    atlas = Image.new(
        "RGBA",
        (sheet["columns"] * tile_size, sheet["rows"] * tile_size),
        (0, 0, 0, 0),
    )

    for obj in spec["objects"]:
        tile_path = tiles_dir / f"{obj['id']}.png"
        if not tile_path.is_file():
            raise SystemExit(f"missing tile for composition: {tile_path}")
        tile = Image.open(tile_path).convert("RGBA")
        atlas.paste(tile, (obj["origin"]["x"] * tile_size, obj["origin"]["y"] * tile_size))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(output_path)


if __name__ == "__main__":
    main()
