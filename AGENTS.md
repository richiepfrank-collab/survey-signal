# AGENTS.md — engineering brief for coding agents

Survey Signal is an open-source aerial threat-signal triage tool for humanitarian mine action: drone RGB imagery → tiled local RT-DETR proposals → human confirm/reject review → georeferenced hazard exports (GeoJSON/KML/HTML report). Built for OpenAI Build Week; submission deadline July 21, 2026. Full project context: `../SESSION_HISTORY.md` (if present) and `BUILD_PLAN.md`.

## Project governance

Before any project work, read and follow [`GovernanceFile.md`](GovernanceFile.md). Its workflow, task-tracking, verification, and lesson-capture rules govern all future repository actions, unless they conflict with higher-priority instructions.

## Commands

```bash
pip install -e ".[dev]"      # install (torch is large)
minemark serve               # run at http://localhost:8000
pytest -q                    # tests must stay green
ruff check backend scripts tests
```

## Architecture

- `backend/app.py` — FastAPI routes. Frontend served at `/`, vendored assets at `/vendor`.
- `backend/store.py` — SQLite session store (`MINEMARK_SESSION`, default `minemark_session/`): images, detections, append-only `review_log`. All state goes through it; do not add in-memory state.
- `backend/detector.py` — tiled inference (TILE=1024, OVERLAP=128), cross-seam NMS. Model selected by `MINEMARK_MODEL`, which must be a fully staged local RT-DETR model directory; no runtime downloads.
- `backend/georef.py` — EXIF GPS → per-pixel WGS84 using height above ground (`MINEMARK_AGL_M` / XMP `RelativeAltitude`), camera yaw, and 35 mm-equivalent focal length. Any assumed input adds a warning and marks positions `unverified`; never silently fall back. GeoTIFFs use their affine transform.
- `backend/exports.py` — GeoJSON/KML (KML is hand-rolled XML; do not re-add simplekml) + Jinja2 HTML report. `DISCLAIMER` constant goes into every export.
- `frontend/index.html` — single file, no build step; Leaflet is vendored under `frontend/vendor/leaflet/`. No external URLs in `src`/`href` (a test enforces this). The backdrop is the uploaded imagery via `/api/image/{id}/preview`; a tile basemap is opt-in through `MINEMARK_BASEMAP_URL`.
- `scripts/prepare_labels.py` — dataset-label adapters (COCO done; add loaders only after inspecting released annotation artifacts).
- `scripts/train.py` — explicit training gate until usable DRC ground truth is available.

## Hard constraints (safety-critical domain)

1. **Never weaken the disclaimer.** Every export and the UI header must state: survey-assist only, surface objects only, never declares land safe. A missing marker means nothing.
2. Exports default to **confirmed-only** detections (`include_unsure` opt-in). Never export pending/rejected as hazards.
3. **Offline-capable at runtime**: no network calls in the detection/review/export path, including the frontend.
4. **Honest metrics**: held-out evaluation must come from a different flight/site than training; report failure cases alongside successes.

## Priorities (from BUILD_PLAN.md)

1. Label converters for the real downloaded datasets (Baur et al. 2026 benchmark, Demining Research Community) — see `data/README.md`.
2. Fine-tune + before/after comparison vs the pretrained baseline.
3. GeoTIFF/orthomosaic ingest (rasterio, optional extra already in pyproject).
4. UI polish: confidence-threshold slider, batch progress, review-queue ordering by confidence.
5. Replace the LICENSE stub with canonical Apache-2.0 text before the repo goes public.

## Conventions

Python 3.10+, ruff (line length 100), type hints on new code, tests for any geometry/export math. Log each Codex work session in `docs/codex-log.md` (judges look at it).
