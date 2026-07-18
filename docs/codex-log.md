# Codex build log

Judges want to see how Codex was used. Append an entry each session — one line is enough.

| Date | What Codex built | Notes |
|---|---|---|
| 2026-07-17 | Initial scaffold: FastAPI pipeline, tiled YOLO detection, EXIF georef, Leaflet review UI | |
| 2026-07-17 | Imported Claude handoff; added GeoTIFF CRS georeferencing, upload validation, confidence filtering, resilient upload feedback, and offline-only local-model enforcement | Build Week hardening pass |
| 2026-07-17 | Drafted Build Week project narrative and a safety-first <3 minute demo script | `SUBMISSION_DRAFT.md` |
| 2026-07-18 | Downloaded and documented a CC-BY DRC pre-burial RGB GeoTIFF; added bounded-window GeoTIFF reads after real-file validation exposed Pillow's large-image limit | 6 tests passing |
| 2026-07-18 | Migrated the runtime model contract from AGPL-licensed Ultralytics YOLO to a local-only Apache-2.0 RT-DETR baseline | Model binaries remain ignored |
| 2026-07-18 | Ran a genuine DRC GeoTIFF through upload, RT-DETR proposal, WGS84 mapping, crop, confirmation, and GeoJSON export | Four generic proposals; no ordnance-quality claim |
| 2026-07-18 | Updated the Build Week narrative to distinguish the verified local generic baseline from a future validated ordnance model | Training remains data-gated |
| 2026-07-18 | Incorporated official Build Week submission requirements into README, submission materials, and a Devpost checklist | External form/video actions remain manual |
| 2026-07-18 | Migrated the runtime model contract from AGPL-licensed Ultralytics YOLO to a local-only Apache-2.0 RT-DETR baseline | Model binaries remain ignored |
