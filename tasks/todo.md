# Survey Signal — Build Week delivery plan

Status: **in progress**

## Goal

Deliver a credible, offline-first Build Week submission: a working local demo,
an Apache-compatible detector path, reproducible evidence, and complete public
submission materials. Survey Signal remains a survey-assist tool only; no step may
weaken its safety disclaimer or imply land clearance.

## Plan

- [x] **1. Establish reproducible data provenance.** Download the smallest DRC
  CC-BY 4.0 RGB GeoTIFF suitable for a demo, record source URL/DOI, license,
  file checksum, and attribution in `data/`. Inspect the released ground-truth
  material before assuming a training-label format.
- [x] **1a. Make large GeoTIFF ingest safe.** The approved DRC pre-burial
  orthomosaic is 312.6 megapixels, exceeding Pillow's decompression-bomb
  threshold. Replace full-image Pillow reads with bounded-window raster reads
  for GeoTIFF detection/cropping, retaining the existing JPEG path and safety
  checks.
- [x] **2. Replace the Ultralytics dependency.** Migrate the detector adapter
  to locally staged Apache-2.0 RT-DETR weights; preserve tiled inference,
  detection schema, seam NMS, and the no-runtime-download guarantee. Update
  dependencies, CLI/startup validation, tests, README, and model provenance.
- [ ] **3. Build the dataset adapter and evaluation protocol.** Implement the
  exact DRC annotation converter after inspection. Create a site-separated
  train/validation/test split and record metrics plus qualitative failure
  cases. Do not publish a detection-rate claim without this held-out evidence.
- [x] **4. Validate the genuine end-to-end workflow.** Run a real GeoTIFF
  through upload, tiled inference, review, and confirmed-only GeoJSON/KML/HTML
  exports. Add regression tests for observed georeferencing, export, and UI
  behavior.
- [ ] **5. Package the submission.** Add polished screenshots, finalize the
  README and `SUBMISSION_DRAFT.md`, record the sub-three-minute demo, and run
  a release-readiness audit (license, reproducibility, safety wording, tests,
  and public-repo hygiene).

## Proposed Build Week rules-compliance plan

Status: **in progress — repository requirements applied; external submission actions pending**

- [x] Add a README Build Week section documenting how Codex and GPT-5.6 were
  used, with links to `docs/codex-log.md` and the implementation evidence.
- [x] Add a submission checklist covering the required English project
  description, public or reviewer-shared repository, track selection, public
  YouTube demo under three minutes with audio, `/feedback` Codex Session ID,
  third-party attribution, and final deadline.
- [x] Update the demo script to explicitly show the local RT-DETR workflow,
  the Codex/GPT-5.6 collaboration evidence, and the safety limitation without
  using unlicensed music, footage, or trademarks.
- [x] Add concise judge setup/testing instructions and the exact DRC/model
  provenance references, while keeping all model and data binaries out of Git.

### Rules findings — 2026-07-18

The official rules require a project built with Codex and GPT-5.6, a category,
an English description, a public YouTube demo with audio shorter than three
minutes, a code-repository URL, and a `/feedback` Codex Session ID. The
repository may be public with relevant licensing or private if shared with
`testing@devpost.com` and `build-week-event@openai.com`. The README must
describe collaboration with Codex and GPT-5.6. Third-party data, models, SDKs,
and media require authorization and license compliance. The submission deadline
is July 21, 2026 at 5:00 pm PDT.

## Decision gates

1. Confirm the DRC release contains usable, legally reusable target labels or
   coordinate ground truth. If it does not, use it for the demo/evaluation
   baseline only and obtain a separately licensed annotation source before
   fine-tuning.
2. Use RT-DETR-R18 only after the adapter and its local model artifact can be
   pinned by version and checksum. Do not retain Ultralytics YOLO in an
   Apache-2.0 distribution without an appropriate commercial license.
3. Stop before any claim of operational detection quality unless a
   different-site held-out evaluation supports that exact claim.

## Expected verification

- Automated tests and Ruff pass.
- The application rejects missing/non-local model files without network access.
- A real DRC GeoTIFF produces correctly positioned reviewed export features.
- All distributed data/model artifacts have a recorded license and provenance.

## Review

### 2026-07-18 — re-plan trigger

The downloaded DRC Field 1 pre-burial RGB GeoTIFF is complete (SHA-256
`9deb1da62bd68df49c81fe125bf6b89eb6a936e051a71966dfcd90be7c2df14a`) and is
312,610,430 pixels. The current `PIL.Image.open` path rejects it under
Pillow's decompression-bomb protection. Large-GeoTIFF bounded-window ingest is
therefore a prerequisite to the planned end-to-end validation, not a stretch
goal.

### 2026-07-18 — provenance and ingest verification

The selected DRC pre-burial asset is recorded in `data/DRC_PROVENANCE.md` with
its source, CC BY 4.0 license, checksum, collection metadata, and raster
properties. Bounded Rasterio reads successfully loaded an interior 1024 × 1024
RGB window and WGS84 center coordinate from the 312.6 MP source. The release
does not contain a ready-to-use object-detection label artifact, so the
fine-tuning/evaluation task remains blocked on released or author-provided
ground-truth coordinates.

### 2026-07-18 — local RT-DETR migration verification

The runtime now uses the staged Apache-2.0 PekingU RT-DETR-R18 directory with
`local_files_only=True`; it produced proposals in a direct CPU inference pass.
The model checksum and staging instructions are recorded in `models/README.md`.
The former Ultralytics dependency and runnable YOLO training script were
removed to avoid an Apache/AGPL licensing mismatch. Fine-tuning is an explicit
gate, not a broken command.

### 2026-07-18 — real API workflow verification

A 1024 × 1024 georeferenced center window from the downloaded DRC Field 1
orthomosaic was uploaded through the FastAPI API using the staged local RT-DETR
model. The run produced four proposals, all with WGS84 coordinates; confirming
one candidate yielded a valid crop response and a confirmed-only GeoJSON export
with exactly one feature. These are generic COCO proposals, not validated
ordnance detections.

### Current blocker

The remaining training/evaluation work requires a released or author-provided,
legally reusable object-level coordinate artifact for the DRC field. This is an
external data-access decision, not a software defect. Submission packaging may
continue with the generic-baseline limitation stated prominently.

## Proposed naming-alignment plan — pending approval

Goal: adopt **Survey Signal** as the reader-facing project name, using
**SurveySignal** only where a compact display form is needed, while preserving
the existing `minemark` package, CLI, environment variables, filenames, and
export identifiers for compatibility.

- [x] Update reader-facing project documents: `README.md`, `DISCLAIMER.md`,
  `SUBMISSION_DRAFT.md`, `SUBMISSION_CHECKLIST.md`, `BUILD_PLAN.md`,
  `AGENTS.md`, and `models/README.md`.
- [x] Update the visible application title and header in `frontend/index.html`
  plus human-readable report/export labels; do not rename the Python package,
  `minemark` CLI, `MINEMARK_*` variables, session directory, or filenames.
- [ ] Update the current Devpost draft name, pitch, and public project story
  only after a separate action-time confirmation to save those external form
  changes.
- [x] Verify no reader-facing `MineMark` references remain, verify the
  application still passes its tests, and record the naming decision in this
  review section.

### 2026-07-18 — Survey Signal naming review

Reader-facing documentation, the browser title/header, FastAPI title, GeoJSON
metadata, KML document name, and HTML report title now use **Survey Signal**.
The compact form **SurveySignal** is reserved for locations that later require
a no-space display identifier; none were needed in the current repository.
The `minemark` package, CLI, `MINEMARK_*` configuration, session directory,
and export filenames deliberately remain stable. `rg` found no remaining
reader-facing `MineMark` references. `pytest -q` passed (6 tests), and
`ruff check backend scripts tests` passed.

## Proposed terminology-alignment plan — pending approval

- [x] Replace the reader-facing phrase **aerial ordnance triage** with
  **aerial threat-signal triage** in `README.md`, `SUBMISSION_DRAFT.md`, and
  `BUILD_PLAN.md`.
- [x] Align the package description in `pyproject.toml` with the same wording;
  leave the stable `minemark` package and CLI identifiers unchanged.
- [x] Verify the obsolete reader-facing phrase is absent, run the existing
  automated checks, and record the result below.

### 2026-07-18 — Terminology-alignment review

`README.md`, `SUBMISSION_DRAFT.md`, `BUILD_PLAN.md`, and `pyproject.toml` now
use **aerial threat-signal triage**. `rg` found no remaining implementation or
reader-facing use of the obsolete phrase outside this completed plan record.
`pytest -q` passed (6 tests), and `ruff check backend scripts tests` passed.

## Post-Build-Week hardening plan — approved by owner 2026-11-17

Goal: fix the three defects that made exported positions and review records
untrustworthy, without touching the detector or the disclaimer.

- [x] **Georeferencing.** Stop treating EXIF GPS altitude (above sea level) as
  height above ground; read XMP relative altitude and yaw; derive GSD from the
  35 mm-equivalent focal length; flag every assumed input.
- [x] **Persistence and audit.** Replace in-memory `STATE` with a SQLite session
  store and an append-only review log (analyst + UTC timestamp).
- [x] **Offline map.** Vendor Leaflet, remove the CDN and OpenStreetMap tile
  requests, and draw the uploaded imagery as the map backdrop.

### 2026-11-17 — review

- `backend/georef.py`: altitude source order is `MINEMARK_AGL_M` → XMP
  `RelativeAltitude` → EXIF GPS altitude (flagged) → 60 m default (flagged).
  Yaw rotates pixel offsets. Each image stores its input sources and warnings;
  detections carry `position_quality`, which appears in the UI and all exports.
- `backend/store.py`: `session.sqlite3` in the session directory; uploads are
  hashed (SHA-256) and recorded with the model path used.
- `frontend/`: Leaflet 1.9.4 vendored; north-up imagery previews served from
  `/api/image/{id}/preview`; tile basemap is opt-in only.
- The HTML report template now autoescapes, because analyst names and file
  names are user-supplied.
- Verification: `pytest -q` 16 passed (rasterio installed). A headless-Chrome
  run against a stand-in detector uploaded a yawed frame, reviewed two
  candidates, and made 15 requests, all to localhost; decisions and reviewer
  names were intact after a server restart.
- Not verified: real DJI imagery (tests use synthetic EXIF/XMP), and preview
  render time on the 312 MP DRC orthomosaic, which has no stored overviews.
- Known limits: flat-ground nadir model; `RelativeAltitude` is relative to the
  take-off point; previews of rotated or projected GeoTIFFs are placed by
  bounding box.
