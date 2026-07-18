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
git clone https://github.com/YOURUSER/minemark && cd minemark
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
        ─► pixel→WGS84 georeferencing (EXIF GPS / GeoTIFF CRS)
        ─► human review UI (Leaflet + crop viewer)
        ─► exports: GeoJSON · KML · HTML survey report
```

- `backend/` — FastAPI app, detection pipeline, georeferencing, exports
- `frontend/` — single-file Leaflet review UI (no build step; vendor Leaflet for fully air-gapped deployments)
- `scripts/` — model staging and dataset-label conversion
- `data/` — open dataset sources ([data/README.md](data/README.md))

## Training your own model

See [data/README.md](data/README.md) for open datasets (Baur et al. 2026 seeded-minefield benchmark, Demining Research Community), then:

```bash
python scripts/prepare_labels.py --source <dataset_dir> --out data/yolo
```

## Status

Hackathon MVP. Detection quality depends entirely on the model you load; the staged baseline is a generic pretrained checkpoint in low-threshold "proposal mode" — useful for demonstrating the workflow, not for real survey. Contributions welcome, especially legally reusable object-level labels from vegetated/tropical terrain.
