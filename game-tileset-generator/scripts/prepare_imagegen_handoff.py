#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a structured image generation request from derived atlas artifacts."
    )
    parser.add_argument("--spec", required=True, help="Path to tileset_spec.json")
    parser.add_argument("--prompt", required=True, help="Path to generation_prompt.txt")
    parser.add_argument("--negative", required=True, help="Path to prompt-negative.txt")
    parser.add_argument("--layout-guide", required=True, help="Path to layout-guide.png")
    parser.add_argument("--output", required=True, help="Output path for imagegen-request.json")
    return parser.parse_args()


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_file(path_str: str, label: str) -> Path:
    path = Path(path_str)
    if not path.is_file():
        raise SystemExit(f"{label} file not found: {path}")
    return path


def build_handoff(
    spec_path: Path,
    positive_prompt: str,
    negative_prompt: str,
    guide_path: Path,
    artifact_dir: Path,
) -> dict:
    spec = read_json(spec_path)
    sheet = spec["sheet"]

    return {
        "spec_path": str(spec_path.resolve().relative_to(artifact_dir.resolve().parent)),
        "view": sheet.get("view", "top-down"),
        "atlas_content": sheet.get("atlas_content"),
        "layout_style": sheet["layout_style"],
        "layout_preset": sheet["layout_preset"],
        "tile_size": sheet["tile_size"],
        "grid": {
            "columns": sheet["columns"],
            "rows": sheet["rows"],
        },
        "expected_atlas_aspect": sheet["columns"] / sheet["rows"],
        "expected_cell_aspect": 1.0,
        "positive_prompt": positive_prompt.rstrip(),
        "negative_prompt": negative_prompt.rstrip(),
        "reference_images": [
            {
                "path": guide_path.name,
                "role": "layout-guide",
                "usage": "layout-only",
                "required": True,
            }
        ],
        "generator": {
            "tool": "$imagegen",
            "mode": "single-atlas-job",
            "requires_layout_reference": True,
        },
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    spec_path = require_file(args.spec, "spec")
    prompt_path = require_file(args.prompt, "prompt")
    negative_path = require_file(args.negative, "negative prompt")
    guide_path = require_file(args.layout_guide, "layout guide")
    handoff = build_handoff(
        spec_path,
        read_text(prompt_path),
        read_text(negative_path),
        guide_path,
        Path(args.output).parent,
    )
    write_json(Path(args.output), handoff)


if __name__ == "__main__":
    main()
