#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a selected worker output into the run folder and update imagegen-jobs.json."
    )
    parser.add_argument("--run-dir", required=True, help="Tileset run directory")
    parser.add_argument(
        "--manifest",
        help="Optional path to imagegen-jobs.json. Defaults to <run-dir>/imagegen-jobs.json",
    )
    parser.add_argument("--job-id", required=True, help="Job id to update")
    parser.add_argument(
        "--selected-source",
        help="Absolute path to the selected generated image. Required when --status=complete",
    )
    parser.add_argument(
        "--status",
        choices=("complete", "failed"),
        default="complete",
        help="Job status to write",
    )
    parser.add_argument(
        "--qa-note",
        default="",
        help="One-line worker note",
    )
    parser.add_argument(
        "--run-postprocess",
        action="store_true",
        help="Run serialized postprocess after copying the selected output",
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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def image_metadata(path: Path) -> dict[str, int]:
    with Image.open(path) as image:
        return {"width": image.width, "height": image.height}


def run_postprocess(run_dir: Path) -> None:
    script_path = Path(__file__).resolve().parent / "process_tileset_run.py"
    subprocess.run(
        [sys.executable, str(script_path), "--run-dir", str(run_dir)],
        check=True,
    )


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else run_dir / "imagegen-jobs.json"
    if not manifest_path.is_file():
        raise SystemExit(f"job manifest not found: {manifest_path}")

    manifest = load_json(manifest_path)
    jobs = manifest.get("jobs", [])
    job = next((entry for entry in jobs if entry.get("id") == args.job_id), None)
    if job is None:
        raise SystemExit(f"job not found: {args.job_id}")

    source_path: Path | None = None
    copied_output = ""
    output_meta: dict[str, int] | None = None

    if args.status == "complete":
        if not args.selected_source:
            raise SystemExit("--selected-source is required when --status=complete")
        source_path = Path(args.selected_source).expanduser().resolve()
        if not source_path.is_file():
            raise SystemExit(f"selected source not found: {source_path}")

        output_rel = job.get("output_path")
        if not output_rel:
            raise SystemExit(f"job has no output_path: {args.job_id}")
        output_path = run_dir / output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, output_path)
        copied_output = relpath_or_abs(output_path, run_dir)
        output_meta = image_metadata(output_path)

    job["status"] = args.status
    job["qa_note"] = args.qa_note
    job["completed_at"] = utc_now()

    if source_path is not None:
        job["selected_source"] = relpath_or_abs(source_path, run_dir)
        job["copied_output_path"] = copied_output
    if output_meta is not None:
        job["copied_output_size_px"] = output_meta

    write_json(manifest_path, manifest)

    if args.run_postprocess:
        run_postprocess(run_dir)


if __name__ == "__main__":
    main()
