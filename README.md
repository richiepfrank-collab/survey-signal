# Survey Signal

**Open-source aerial threat-signal triage.** Upload drone imagery → AI flags candidate surface objects → a human analyst confirms or rejects each flag → export a georeferenced hazard map (GeoJSON/KML) and survey report for accredited mine-action teams.

> ⚠️ **[Read the disclaimer](DISCLAIMER.md).** Survey Signal is a survey-assist research tool. It does not detect buried mines, it does not achieve humanitarian-clearance reliability, and it must never be used to declare land safe. Humans stay in the loop by design.

Built for [OpenAI Build Week](https://openai.com/build-week/) with Codex. Apache-2.0.

## Build Week: how Codex was used

Survey Signal was built and meaningfully extended during Build Week in Codex. Codex
was used to design and implement the FastAPI workflow, bounded-window GeoTIFF
ingest, local-only RT-DETR inference adapter, human review UI, georeferenced
exports, automated tests, data/model provenance, and this documentation.

The engineering trail is intentionally public: see the dated
[Codex build log](docs/codex-log.md), the governed
[task record](tasks/todo.md), and the [submission draft](SUBMISSION_DRAFT.md).
Before submitting, the entrant must verify that the required GPT-5.6 usage and
the `/feedback` Codex Session ID are correctly represented in Devpost; do not
make a claim that the session evidence cannot support.

## Why

Drone RGB imagery + AI detects ~95% of surface-laid ordnance in peer-reviewed field benchmarks, and runs operationally at scale in Ukraine — on proprietary platforms. The most mine-affected low-income countries have no access to this capability. Survey Signal is the open, offline-capable version.

## Quickstart

```bash
git clone https://github.com/richiepfrank-collab/survey-signal && cd survey-signal
pip install -e .
MINEMARK_MODEL=/absolute/path/to/local-model-directory minemark serve
```

Upload GPS-tagged drone JPEGs or PNGs, review detections on the map (keys: **y** confirm / **n** reject / **u** unsure), then export GeoJSON, KML, or an HTML survey report. GeoTIFF orthomosaics are also supported after `pip install -e ".[geotiff]"`.

Survey Signal will not download a model at runtime. Stage approved detector weights locally, then start it with `MINEMARK_MODEL=models/rtdetr-r18vd minemark serve`. This preserves the offline operating model and makes the exact model used in a survey traceable. The development baseline is Apache-2.0 RT-DETR-R18, a generic COCO proposal model—not an ordnance detector. See [models/README.md](models/README.md).

For GeoTIFF imagery, install the optional local reader first:

```bash
pip install -e ".[geotiff]"
python scripts/stage_model.py --repo PekingU/rtdetr_r18vd --out models/rtdetr-r18vd
MINEMARK_MODEL=models/rtdetr-r18vd minemark serve
```

## Positions, sessions, and offline use

**Marker positions.** GeoTIFF orthomosaics are positioned exactly from their transform. For
single GPS-tagged photos, Survey Signal estimates the ground footprint and records where each
input came from:

| Input | Preferred source | Fallback (flagged as *unverified*) |
|---|---|---|
| Height above ground | `MINEMARK_AGL_M`, then DJI XMP `RelativeAltitude` | EXIF GPS altitude, which is height above **sea level** |
| Camera heading | XMP gimbal/flight yaw, then EXIF `GPSImgDirection` | assumed north-up |
| Lens field of view | EXIF 35 mm-equivalent focal length | assumed 13.2 mm sensor width |

If your imagery has no relative altitude, set the flight height yourself, for example
`MINEMARK_AGL_M=40 minemark serve`. Every detection carries a `position_quality` of
`georeferenced`, `approximate`, or `unverified` in the UI, GeoJSON, KML, and report, and the
report lists the reason for each unverified image. `RelativeAltitude` is height above the
take-off point, so sloping ground still shifts markers.

**Sessions and audit trail.** Imagery, detections, and review decisions are stored in
`minemark_session/session.sqlite3` and survive a restart. Every confirm/reject/unsure is
appended to a review log with the analyst name entered in the header and a UTC timestamp
(`GET /api/audit`). Use `MINEMARK_SESSION=/path/to/survey-042` to keep surveys separate; back
up or archive that directory to preserve a survey.

**Offline review.** Leaflet is vendored in `frontend/vendor/leaflet/`, and the map backdrop is
your own uploaded imagery rendered locally, so the review UI makes no external requests. To
add a tile basemap on a connected machine, opt in with
`MINEMARK_BASEMAP_URL='https://tile.example.org/{z}/{x}/{y}.png'` (and
`MINEMARK_BASEMAP_ATTRIBUTION`); check the tile provider's usage terms first.

## Judge setup and testing

Survey Signal is a local web application, not a hosted service. Follow the GeoTIFF
quickstart above, open `http://127.0.0.1:8000`, and upload a GPS-tagged image or
GeoTIFF. Confirm one proposal with `y`, then download GeoJSON from the header.

For a reproducible public test asset, use the CC-BY DRC Field 1 pre-burial
orthomosaic and its recorded checksum in [data/DRC_PROVENANCE.md](data/DRC_PROVENANCE.md).
The staged RT-DETR baseline is generic COCO object detection; it validates the
review workflow only and must not be treated as an ordnance-quality model.

See [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for Devpost-only
requirements, licenses, and video constraints.

## Architecture

```
images ─► bounded overlapping tiles ─► local RT-DETR detector ─► seam-aware NMS
        ─► pixel→WGS84 georeferencing (EXIF GPS + flight geometry / GeoTIFF CRS)
        ─► SQLite session store + review audit log
        ─► human review UI (Leaflet + crop viewer)
        ─► exports: GeoJSON · KML · HTML survey report
```

- `backend/` — FastAPI app, detection pipeline, georeferencing, exports
- `frontend/` — single-file review UI with vendored Leaflet 1.9.4 (BSD-2-Clause; no build step, no CDN)
- `scripts/` — model staging and dataset-label conversion
- `data/` — open dataset sources ([data/README.md](data/README.md))

## Training your own model

See [data/README.md](data/README.md) for open datasets (Baur et al. 2026 seeded-minefield benchmark, Demining Research Community), then:

```bash
python scripts/prepare_labels.py --source <dataset_dir> --out data/yolo
```

## Status

Hackathon MVP. Detection quality depends entirely on the model you load; the staged baseline is a generic pretrained checkpoint in low-threshold "proposal mode" — useful for demonstrating the workflow, not for real survey. Contributions welcome, especially legally reusable object-level labels from vegetated/tropical terrain.
