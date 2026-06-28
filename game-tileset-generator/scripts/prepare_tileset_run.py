#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from prepare_imagegen_handoff import build_handoff, write_json as write_handoff_json
from prepare_tileset_spec import build_spec, load_json as load_spec_json, write_json as write_spec_json
from render_generation_prompt import build_negative_prompt, build_positive_prompt, load_spec as load_prompt_spec, validate_spec as validate_prompt_spec
from render_layout_guide import load_spec as load_layout_spec, render as render_layout_image, validate_objects


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a tileset run folder from a tileset spec."
    )
    parser.add_argument("--run-dir", required=True, help="Output run directory")
    parser.add_argument("--spec", required=True, help="Path to the confirmed tileset spec input")
    parser.add_argument("--request", help="Optional path to request.json to copy into the run folder")
    parser.add_argument("--force", action="store_true", help="Replace an existing run directory")
    return parser.parse_args()


def ensure_clean_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise SystemExit(f"run directory already exists: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_if_present(source: str | None, target: Path) -> None:
    if source is None:
        return
    src_path = Path(source)
    if not src_path.is_file():
        raise SystemExit(f"request file not found: {src_path}")
    shutil.copy2(src_path, target)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def relpath(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def build_imagegen_jobs(run_dir: Path, spec: dict, handoff_path: Path, handoff: dict) -> dict:
    sheet = spec["sheet"]
    return {
        "jobs": [
            {
                "id": "atlas",
                "kind": "atlas-generation",
                "status": "ready",
                "spec_path": relpath(run_dir / "tileset_spec.json", run_dir),
                "request_file": relpath(handoff_path, run_dir),
                "input_images": [
                    {
                        **image,
                        "path": str(Path("references") / image["path"]),
                    }
                    for image in handoff["reference_images"]
                ],
                "required_reference_roles": ["layout-guide"],
                "requires_layout_reference": True,
                "output_path": relpath(run_dir / "decoded" / "atlas-candidate.png", run_dir),
                "layout_style": sheet["layout_style"],
                "layout_preset": sheet["layout_preset"],
                "view": sheet.get("view", "top-down"),
                "atlas_content": sheet.get("atlas_content"),
                "tile_size": sheet["tile_size"],
                "grid": {
                    "columns": sheet["columns"],
                    "rows": sheet["rows"],
                },
            }
        ],
    }


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    ensure_clean_dir(run_dir, args.force)

    for subdir in ("decoded", "final", "qa", "tiles", "references"):
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    source_spec = load_spec_json(Path(args.spec))
    spec = build_spec(source_spec)

    spec_path = run_dir / "tileset_spec.json"
    layout_guide_path = run_dir / "references" / "layout-guide.png"
    handoff_path = run_dir / "references" / "imagegen-request.json"
    jobs_path = run_dir / "imagegen-jobs.json"
    request_path = run_dir / "request.json"

    copy_if_present(args.request, request_path)
    write_spec_json(spec_path, spec)

    prompt_spec = load_prompt_spec(spec_path)
    layout_style = validate_prompt_spec(prompt_spec)
    positive_prompt = build_positive_prompt(prompt_spec, layout_style)
    negative_prompt = build_negative_prompt(layout_style)

    layout_spec = load_layout_spec(spec_path)
    validate_objects(layout_spec)
    render_layout_image(layout_spec, layout_guide_path, cell_px=112, padding=0)

    handoff = build_handoff(
        spec_path,
        positive_prompt,
        negative_prompt,
        layout_guide_path,
        handoff_path.parent,
    )
    write_handoff_json(handoff_path, handoff)
    write_json(jobs_path, build_imagegen_jobs(run_dir, spec, handoff_path, handoff))


if __name__ == "__main__":
    main()
