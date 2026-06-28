# Scripts

These scripts are organized by pipeline stage.

## Shared Stages

Spec and run preparation:
- `prepare_tileset_spec.py`
- `prepare_tileset_run.py`
- `complete_tileset_job.py`
- `process_tileset_run.py`

Derived references:
- `render_layout_guide.py`
- `render_generation_prompt.py`
- `prepare_imagegen_handoff.py`

## Full Variant

These implement the shared stages for the `full` tileset style:
- `validate_full_candidate.py`
- `extract_full_tiles.py`
- `validate_full_atlas.py`
- `compose_full_atlas.py`

## Partial Variant

These implement the shared stages for the `partial` tileset style:
- `validate_partial_candidate.py`
- `extract_partial_tiles.py`
- `validate_partial_atlas.py`
- `compose_partial_atlas.py`

## Design Rule

The pipeline shape is shared:

`prepare -> derive -> generate -> candidate-validate -> extract -> tile-validate -> compose`

Different tileset types should add different stage implementations, not a different top-level flow.

## Orchestration Rule

- `prepare_tileset_spec.py` validates and normalizes an AI-authored spec draft
- `prepare_tileset_run.py` writes the run folder and `imagegen-jobs.json`
- workers read prompt/layout/spec paths from run artifacts
- generation workers must attach the layout guide as a real reference image
- the parent records a selected worker output with `complete_tileset_job.py`
- `complete_tileset_job.py --run-postprocess` combines record + serialized postprocess
- the parent then runs `process_tileset_run.py --run-dir <run-dir>`
- `process_tileset_run.py` serializes candidate validation, extraction, tile validation, and composition
- `process_tileset_run.py` locks one run so the same run cannot be postprocessed concurrently
- postprocess stage scripts still support `--run-dir` for direct debugging
- `extract_full_tiles.py` is allowed to reject a candidate before extraction when atlas geometry does not match the spec closely enough
- `extract_partial_tiles.py` removes the chroma-key background into alpha before validation and composition

## Repo Hygiene

Keep scripts here focused on reusable pipeline behavior.

Do not place demo outputs in `scripts/`.
Demo inputs and artifacts should live under `../demo/`.
