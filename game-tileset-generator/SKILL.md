---
name: game-tileset-generator
description: Turn user intent into atlas-based game tilesets through a production spec, layout-guided image generation, and deterministic postprocess stages.
---

# Game Tileset Generator

## Overview

This skill turns a user request into an atlas-based tileset that can move through a stable production flow.

## Dependencies

Required:
- the installed `imagegen` skill
- a runnable Python interpreter
- Pillow

Notes:
- `$imagegen` is used for all image generation in this skill
- a runnable Python interpreter runs the prepare, extract, validate, and compose scripts
- Pillow is required by those scripts for image read, crop, resize, QA, and atlas composition

If any dependency is missing:
- stop the skill flow
- tell the user which dependency is missing
- suggest how to install or enable it

## Spec Confirmation

Turn the user request into a proposed spec, then normalize the approved version into `tileset_spec.json`.

Do not ask the user to define the whole spec from scratch.
Start from the user request, infer a reasonable proposal, then ask the user to confirm or adjust it.

Confirmation gate:
- do not start `prepare_tileset_spec.py`, `prepare_tileset_run.py`, generation, or any downstream script until the user has explicitly approved the full proposed spec
- if the user changes one or more items, restate the full current proposal and wait again
- a partial adjustment is not final approval by itself
- only proceed after the user gives a clear affirmative go-ahead that means the spec is approved and generation may start
- examples: `go ahead`, `looks good, generate it`, `approved, start generation`
- if the reply does not clearly mean approval to start, the flow is still in confirmation
- before asking for approval, include your recommendation for each key item and explain the tradeoff briefly

Confirm these items:
- tile size
  common sizes: `16x16`, `32x32`, `64x64`, `128x128`
  suggest a default based on the user's target style and detail level
  means the pixel size of one tile
  affects how much detail each tile can carry and the final atlas size
- pixel style
  options: `full` or `partial`
  `full` means each tile fills its assigned area edge-to-edge
  `partial` means artwork uses only part of the assigned area and keeps empty space around it
  affects prompt wording, layout guide style, extraction rules, and QA rules
  recommendation: usually use `full` for `terrain`, and `partial` for `placed-object`
- view
  options: `top-down`, `three-quarter`, `side-view`, `front-view`, `isometric`
  means the gameplay camera angle the tileset is drawn for
  mainly affects generation prompt wording and how objects should be drawn to read correctly in-game
- object layout size
  means how many objects go into one atlas, which objects they are, and how many tiles each object occupies
  default object size: `1x1`
  also supports `MxN`, such as `2x1` or `2x2`
  affects sheet size, atlas aspect ratio, extraction size, and final composition
- atlas content
  means what this atlas should contain
  options: `terrain`, `placed-object`
  also includes the concrete object list for that atlas
  affects prompt content, object layout, extraction targets, and final atlas contents
- repeatability
  options: `none`, `both`, `horizontal`, `vertical`
  means whether a tile should look seamless when repeated
  affects prompt wording and seam QA checks

If information is missing:
- ask follow-up questions until the missing choice is clear
- give a suggested default first, then ask for confirmation or adjustment
- use plain language first, then include the spec term
- explain what each choice changes
- give a recommendation when one choice is more suitable
- avoid silently filling critical choices when they change prompt, layout, extraction, or QA behavior

Hard constraints:
- one atlas uses one pixel style
- one atlas uses one view
- one atlas uses one atlas content type
- one atlas uses one span convention
- one atlas uses one repeatability convention

## Storage

The run directory stores one execution of the flow.

Storage rules:
- default run directory: `./game-tileset-generator/<run-name>`
- allow user-specified run directories
- do not default to the installed skill directory
- keep all stage artifacts inside the run directory

Recommended run layout:

```text
<run-dir>/
├── request.json
├── tileset_spec.json
├── imagegen-jobs.json
├── references/
│   ├── imagegen-request.json
│   └── layout-guide.png
├── decoded/
│   └── atlas-candidate.png
├── qa/
│   ├── candidate-review.json
│   └── review.json
├── tiles/
│   ├── object-a.png
│   └── ...
├── final/
│   └── atlas.png
```

## Workflow

Overview:

`request -> spec -> derived references -> generation -> candidate validation -> extraction -> tile validation -> composition -> delivery`

Default workflow:

1. Confirm dependencies, atlas spec, and run directory.
Input: user request, active environment
Output: confirmed execution conditions
Action: stop early if `imagegen`, Python, or Pillow is missing.

2. Turn the user request into a proposed spec.
Input: user request
Output: AI-authored proposed spec
Action: infer a reasonable proposal first, give recommendations for the key atlas settings and atlas content, then ask the user to confirm or adjust them.

3. Wait for explicit user approval of the full proposed spec.
Input: AI-authored proposed spec, user feedback
Output: approved spec
Action: if the user changes any item, restate the full current proposal and wait again. Do not start scripts yet. Only a clear affirmative go-ahead counts as approval.

4. Normalize the approved spec into `tileset_spec.json`.
Input: approved spec
Output: `tileset_spec.json`
Script: `scripts/prepare_tileset_spec.py`
Action: reject invalid combinations before any generation starts.

5. Prepare the run directory.
Input: `tileset_spec.json`, optional `request.json`
Output: run folder, `imagegen-jobs.json`
Script: `scripts/prepare_tileset_run.py`
Action: create the standard run structure and write the files later stages expect.

6. Derive generation references from the spec.
Input: `tileset_spec.json`
Output: `references/layout-guide.png`, `references/imagegen-request.json`
Scripts: `scripts/render_layout_guide.py`, `scripts/render_generation_prompt.py`, `scripts/prepare_imagegen_handoff.py`
Action: keep layout, prompt, and imagegen request aligned to the same spec.

7. Dispatch generation work.
Input: `imagegen-jobs.json`, `references/imagegen-request.json`, `references/layout-guide.png`
Output: one or more worker outputs
Tool: `$imagegen`
Action: use the layout guide as a real reference image, not just a file path mention. After choosing one output, return its local path immediately.

8. Record the selected generation output into the run directory.
Input: selected worker image path
Output: updated `imagegen-jobs.json`, `decoded/atlas-candidate.png`
Script: `scripts/complete_tileset_job.py`
Action: copy the chosen result into the standard decoded path immediately after generation, then continue. Use `--run-postprocess` when the parent wants one command for record + serialized postprocess.

9. Run deterministic postprocess in one serialized call.
Input: `tileset_spec.json`, `decoded/atlas-candidate.png`
Output: `qa/candidate-review.json`, `tiles/*.png`, `qa/review.json`, `final/atlas.png`
Script: `scripts/process_tileset_run.py`
Action: this is the only parent entrypoint for postprocess. Do not start candidate validation, extraction, tile validation, or composition as separate parallel commands.

10. Validate the generated candidate before extraction.
Input: `tileset_spec.json`, `decoded/atlas-candidate.png`
Output: `qa/candidate-review.json`
Script: `scripts/validate_full_candidate.py` or `scripts/validate_partial_candidate.py`
Action: reject candidates whose overall atlas geometry does not match the spec closely enough.

11. Extract normalized tiles from the accepted candidate.
Input: `tileset_spec.json`, `decoded/atlas-candidate.png`
Output: `tiles/*.png`, extraction manifest
Script: `scripts/extract_full_tiles.py` or `scripts/extract_partial_tiles.py`
Action: crop by spec layout, then normalize each object footprint into its target size.

12. Validate extracted tiles.
Input: `tileset_spec.json`, `tiles/*.png`
Output: `qa/review.json`
Script: `scripts/validate_full_atlas.py` or `scripts/validate_partial_atlas.py`
Action: run deterministic tile checks before atlas composition.

13. Compose the final atlas.
Input: `tileset_spec.json`, validated tiles
Output: `final/atlas.png`
Script: `scripts/compose_full_atlas.py` or `scripts/compose_partial_atlas.py`
Action: compose only after validation passes.

14. Deliver or iterate.
Input: `qa/candidate-review.json`, `qa/review.json`, `final/atlas.png`
Output: finished atlas or another generation attempt
Action: if QA fails, revise the spec or regenerate; if QA passes, deliver the final atlas and run artifacts.

## Workers Delegation

Main flow responsibilities:
- prepare and normalize the spec
- prepare the run folder
- derive layout and prompt references
- dispatch workers
- copy selected generation output into `decoded/`
- run `scripts/process_tileset_run.py`
- decide whether repair is needed

Worker responsibilities:
- generation worker runs `$imagegen` from derived references
- generation worker selects one candidate output
- visual QA worker checks generated imagery for layout and obvious failures

Worker rules:
- one generation worker per atlas-generation job
- workers do not rewrite the production spec
- workers do not write downstream production outputs outside the assigned job
- the parent inspects QA artifacts, not every raw candidate

Worker return format:
- `selected_source=<worker-local-path-to-selected-output.png>`
- `qa_note=<one sentence>`

Generation worker prompt:

```text
Generate one tileset atlas candidate.

Run directory: <run-dir>
Spec: <run-dir>/tileset_spec.json
Imagegen request: <run-dir>/references/imagegen-request.json

Before calling $imagegen, load the layout guide image into the worker context and attach it as a real reference image.
Use $imagegen. Follow the merged request and attached layout guide. Do not continue without the attached guide. Pick one output.

Return exactly:
selected_source=<worker-local-path-to-selected-output.png>
qa_note=<one sentence>
```

Visual QA worker prompt:

```text
Review one generated tileset artifact.

Run directory: <run-dir>
Spec: <run-dir>/tileset_spec.json
Target image: <path-to-image-under-review>

Check layout adherence, missing tiles, visible guide marks, border artifacts, and obvious style or layout failures.

Return exactly:
qa_status=pass|fail
qa_note=<one sentence>
```

## Tileset Rules

Supported pixel styles:
- `full`
- `partial`

Atlas-wide rules:
- one atlas uses one pixel style
- one atlas uses one view
- one atlas uses one atlas content type
- one atlas uses one span convention
- one atlas uses one repeatability convention
- prompt, layout, extract, and QA rules all derive from the spec

`full` rules:
- each object fills its assigned footprint edge-to-edge
- repeatable tiles should tile cleanly in their declared directions
- candidate atlas geometry must match the spec closely enough before extraction
- reject square or portrait candidates when the spec expects a landscape atlas
- reject candidates whose cells do not read as square

`partial` rules:
- use `chroma_key` for non-art background where required
- preserve safe area around smaller objects
- keep artwork inside the assigned footprint
- convert the chroma-key background to transparency during extraction
- remove chroma spill from semi-transparent edges during extraction

Prompt derivation rules:
- generate prompt text from the spec
- generate negative constraints from pixel style
- `full` and `partial` use different negative constraints
- layout guide and prompt must describe the same sheet geometry

QA rules:
- the spec defines what is checked
- scripts implement the checks
- visual workers handle non-deterministic visual review

Current `full` QA checks:
- candidate atlas aspect ratio before extraction
- candidate cell aspect ratio before extraction
- expected tile size
- unexpected transparency
- seam continuity based on `repeatability`

Current `partial` QA checks:
- candidate atlas aspect ratio before extraction
- candidate cell aspect ratio before extraction
- expected tile size
- non-empty visible pixels
- transparency preserved after chroma-key removal
- no chroma-key fringe or purple spill on semi-transparent edges
