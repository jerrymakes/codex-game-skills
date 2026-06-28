#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run tileset postprocess stages sequentially for one run directory."
    )
    parser.add_argument("--run-dir", required=True, help="Tileset run directory")
    parser.add_argument(
        "--allow-compose-on-qa-fail",
        action="store_true",
        help="Still compose final/atlas.png even when tile QA fails",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def relpath_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def select_scripts(layout_style: str) -> dict[str, str]:
    if layout_style == "full":
        return {
            "candidate_validate": "validate_full_candidate.py",
            "extract": "extract_full_tiles.py",
            "tile_validate": "validate_full_atlas.py",
            "compose": "compose_full_atlas.py",
        }
    if layout_style == "partial":
        return {
            "candidate_validate": "validate_partial_candidate.py",
            "extract": "extract_partial_tiles.py",
            "tile_validate": "validate_partial_atlas.py",
            "compose": "compose_partial_atlas.py",
        }
    raise SystemExit(f"unsupported sheet.layout_style: {layout_style}")


def run_step(script_name: str, run_dir: Path) -> None:
    script_path = SCRIPT_DIR / script_name
    subprocess.run(
        [sys.executable, str(script_path), "--run-dir", str(run_dir)],
        check=True,
    )


def ensure_prerequisites(run_dir: Path) -> Path:
    spec_path = run_dir / "tileset_spec.json"
    candidate_path = run_dir / "decoded" / "atlas-candidate.png"
    if not spec_path.is_file():
        raise SystemExit(f"missing spec: {spec_path}")
    if not candidate_path.is_file():
        raise SystemExit(f"missing decoded candidate: {candidate_path}")
    return spec_path


def acquire_lock(run_dir: Path) -> Path:
    lock_dir = run_dir / ".process-lock"
    try:
        lock_dir.mkdir()
    except FileExistsError:
        raise SystemExit(f"run is already being processed: {run_dir}")
    return lock_dir


def update_manifest_status(
    run_dir: Path,
    *,
    candidate_ok: bool,
    tile_ok: bool,
    composed: bool,
) -> None:
    manifest_path = run_dir / "imagegen-jobs.json"
    if not manifest_path.is_file():
        return

    manifest = load_json(manifest_path)
    jobs = manifest.get("jobs", [])
    if not jobs:
        return

    job = jobs[0]
    job["postprocess"] = {
        "candidate_review_path": relpath_or_abs(run_dir / "qa" / "candidate-review.json", run_dir),
        "candidate_ok": candidate_ok,
        "tile_review_path": relpath_or_abs(run_dir / "qa" / "review.json", run_dir),
        "tile_ok": tile_ok,
        "final_atlas_path": relpath_or_abs(run_dir / "final" / "atlas.png", run_dir) if composed else "",
        "composed": composed,
    }
    job["status"] = "postprocessed" if tile_ok else "qa-failed"
    write_json(manifest_path, manifest)


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    spec_path = ensure_prerequisites(run_dir)
    lock_dir = acquire_lock(run_dir)

    try:
        spec = load_json(spec_path)
        scripts = select_scripts(spec["sheet"]["layout_style"])

        for subdir in ("tiles", "qa", "final"):
            target = run_dir / subdir
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)

        run_step(scripts["candidate_validate"], run_dir)
        candidate_review = load_json(run_dir / "qa" / "candidate-review.json")
        candidate_ok = bool(candidate_review.get("ok", False))
        if not candidate_ok:
            update_manifest_status(run_dir, candidate_ok=False, tile_ok=False, composed=False)
            raise SystemExit("candidate validation failed; see qa/candidate-review.json")

        run_step(scripts["extract"], run_dir)
        run_step(scripts["tile_validate"], run_dir)

        tile_review = load_json(run_dir / "qa" / "review.json")
        tile_ok = bool(tile_review.get("ok", False))

        composed = False
        if tile_ok or args.allow_compose_on_qa_fail:
            run_step(scripts["compose"], run_dir)
            composed = True

        update_manifest_status(
            run_dir,
            candidate_ok=candidate_ok,
            tile_ok=tile_ok,
            composed=composed,
        )

        if not tile_ok:
            raise SystemExit("tile validation failed; see qa/review.json")
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
