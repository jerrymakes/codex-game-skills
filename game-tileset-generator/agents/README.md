# Agents

Roles:
- parent orchestrator
- generation worker
- visual QA worker

Contract:
- the parent owns spec preparation, script execution, and run-folder state
- workers own one assigned visual task at a time
- handoff happens through artifact paths in the run folder
- generation workers must attach `references/layout-guide.png` as a real reference image before calling `$imagegen`
- the parent must postprocess through one serialized call to `scripts/process_tileset_run.py`
- the parent may use `scripts/complete_tileset_job.py --run-postprocess` to combine record + postprocess

Worker return format:
- `selected_source=<worker-local-path-to-selected-output.png>`
- `qa_note=<one sentence>`
