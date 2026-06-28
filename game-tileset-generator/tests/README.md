# Tests

Smoke tests should cover:
- `prepare_tileset_spec.py` normalizing an AI-authored spec draft
- `prepare_tileset_run.py` writing `imagegen-jobs.json`
- `complete_tileset_job.py` copying a selected worker output into `decoded/`
- `process_tileset_run.py --run-dir`
- `validate_full_candidate.py --run-dir`
- `extract_full_tiles.py --run-dir`
- `validate_full_atlas.py --run-dir`
- `compose_full_atlas.py --run-dir`
- `validate_partial_candidate.py --run-dir`
- `extract_partial_tiles.py --run-dir`
- `validate_partial_atlas.py --run-dir`
- `compose_partial_atlas.py --run-dir`
