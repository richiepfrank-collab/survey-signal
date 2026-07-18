# Survey Signal — Build Week submission draft

## Tagline

Open-source, offline aerial threat-signal triage for accredited mine-action teams.

## Problem

Landmines and explosive remnants of war caused at least 6,279 casualties in
2024. Drone imagery can help identify visible surface hazards, but the
operational tooling is concentrated in proprietary, Ukraine-focused programs.
Teams in lower-income mine-affected countries need an affordable way to turn
imagery into a reviewable survey input—without pretending that AI can clear a
minefield.

## What we built

Survey Signal is a local-first web application that turns drone imagery into a
human-reviewed, georeferenced hazard-candidate map:

1. An analyst uploads GPS-tagged imagery or a GeoTIFF orthomosaic.
2. Survey Signal slices large imagery into bounded overlapping tiles, runs a locally
   staged RT-DETR model, and merges duplicate tile-edge proposals with non-maximum
   suppression.
3. A fast keyboard review loop lets an analyst confirm, reject, or defer each
   candidate while seeing its crop and map position.
4. Confirmed candidates export as GeoJSON, KML, and a printable survey report
   for use in an accredited operator's existing workflow.

The app never downloads a model at runtime. The operator explicitly selects
approved local weights before a mission, keeping imagery and the inference path
offline and making the model used in each run auditable.

## Why it matters

Survey Signal is designed as a technical partner tool, not a clearance system. It
helps an accredited operator prioritize suspected areas for proper
IMAS-compliant survey and clearance. It is deliberately opinionated about its
limits: it represents candidate **surface** objects only, requires human review,
and always states that unmarked land may still be hazardous.

## Technical implementation

- FastAPI backend with batch image upload and an intentionally simple
  in-memory MVP state model.
- Large-image tiled inference (1024 px tiles, 128 px overlap) and seam-aware
  IoU NMS.
- Bounded-window GeoTIFF reads, validated against a 312.6 MP CC-BY DRC
  orthomosaic without materializing the full raster in memory.
- A locally staged Apache-2.0 RT-DETR-R18 baseline; it runs with
  `local_files_only=True` and is explicitly a generic COCO proposal model, not
  an ordnance model.
- EXIF GPS pixel-to-WGS84 georeferencing for nadir imagery, plus optional
  GeoTIFF affine/CRS georeferencing.
- Leaflet review interface with confidence filtering and `y` / `n` / `u`
  keyboard decisions.
- Confirmed-only-by-default GeoJSON and KML exports, and an HTML report that
  embeds the safety disclaimer.
- Tests covering tile seam merging, georeferencing math, confirmed-only export,
  and offline model enforcement.

## How we used Codex

Codex was used to scaffold and harden the complete project: the FastAPI API,
tiled detection pipeline, EXIF/GeoTIFF georeferencing, export formats,
single-file review UI, tests, CI, documentation, and this submission material.
The session-by-session implementation log is in `docs/codex-log.md`.

**Before submitting:** add the verified `/feedback` Codex Session ID and ensure
the final wording accurately reflects the required GPT-5.6 usage evidenced by
that session. Do not guess either item.

## Demo script (under 3 minutes)

**0:00–0:20 — Context.** “Survey Signal is not a mine detector and never declares
land safe. It helps accredited teams turn drone imagery into a smaller,
human-reviewed survey queue.” Show the disclaimer.

**0:20–1:30 — Workflow.** Upload a prepared DRC GeoTIFF window. Point out the
local model path, no-cloud runtime, and that the shown proposals come from a
generic baseline pending an ordnance fine-tune. Let proposals appear, use the
confidence slider, open crops, then rapidly confirm/reject with `y` and `n`.

**1:30–2:10 — Outputs.** Download GeoJSON, open it in QGIS or Google Earth,
then show the survey report’s model name, review counts, and prominent warning.

**2:10–2:45 — Technical depth and impact.** Show the tiled inference diagram
in the README, the tests, and the Codex log. Explain the verified Codex/GPT-5.6
contribution, then the intended handoff to an accredited operator in an
under-served mine-affected country. Use original narration and only licensed
media; the public YouTube video must include clear audio and stay under three
minutes.

## Safety statement (include verbatim in the video and submission)

Survey Signal is a survey-assist research tool, not a clearance or land-release
system. It marks AI-flagged, human-reviewed candidate surface objects. A missing
marker does not mean an area is safe; buried hazards are outside its scope.
Only accredited mine-action operators may use its output as an input to an
IMAS-compliant survey process.

## Before submitting

- Replace this draft’s temporary demo references with actual images/video.
- Run a held-out, different-site model evaluation; report both metrics and
  failure cases. Do not claim a detection rate until that experiment is done.
- Record the staged model directory and SHA-256 from `models/README.md` in the
  demo/report.
- Publish the repository, tag `v0.1.0`, and link the video and repo in Devpost.
