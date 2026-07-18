# Survey Signal — OpenAI Build Week Plan
### Open-source aerial threat-signal triage: drone imagery → AI-flagged candidates → human review → georeferenced hazard map

> **2026-07-18 update:** the original YOLO/Ultralytics model path below has
> been superseded by a local Apache-2.0 RT-DETR baseline. The historical scope,
> safety constraints, and delivery plan remain useful; follow `AGENTS.md` and
> `tasks/todo.md` for the current implementation contract.

**Event:** OpenAI Build Week (submissions close **Mon July 21, 5pm PT** — confirm exact time on Devpost)
**Today:** Thu July 17 → you have ~4 working days.
**Build tool:** Codex (required by the event — use it for all scaffolding, refactors, and the frontend).

---

## 1. The pitch (30 seconds)

In Ukraine, drone imagery + AI now finds surface-laid ordnance at ~95% detection rates — but the tooling is proprietary and Ukraine-only. The most mine-affected poor countries (Cambodia, Laos, Angola, South Sudan) have nothing. Survey Signal is the missing open-source version: upload drone imagery, AI flags candidate ordnance, a human analyst confirms or rejects each flag, and the output is a georeferenced hazard map (GeoJSON/KML) an accredited demining operator can feed into their survey workflow. Offline-capable, commodity hardware, Apache-licensed.

**What it is NOT (say this in the demo):** Survey Signal never declares land safe. It is a survey-assist tool that shrinks the suspected area so accredited human deminers spend clearance effort where it matters. False negatives kill; humans stay in the loop by design.

---

## 2. MVP definition (what must work by July 21)

1. **Ingest:** upload one or more drone RGB images (JPEG/PNG with EXIF GPS, or a GeoTIFF orthomosaic).
2. **Tile + detect:** slice large images into overlapping tiles, run a YOLO-class detector, merge detections (NMS across tile seams).
3. **Review UI:** web map (Leaflet) showing imagery footprint + detection markers; click a marker → see the image crop → Confirm / Reject / Unsure. Keyboard shortcuts (y/n/u) for speed.
4. **Export:** GeoJSON + KML of confirmed hazards, plus a printable HTML survey report (date, operator, imagery source, model version, confidence stats, disclaimer).
5. **Runs offline:** single `pip install -e . && minemark serve` on a laptop, no cloud dependency.

**Stretch goals (only if MVP is done):** fine-tuned ordnance model beating the pretrained baseline; PDF report; Spanish/Khmer UI strings; batch orthomosaic mode; confidence-threshold slider with live re-filter.

**Explicit non-goals for the week:** buried-mine detection, thermal/multispectral/GPR payloads, flight planning, anything claiming IMAS-grade reliability.

---

## 3. Model plan (the risky part — de-risked)

Two-track so a training failure can't sink the demo:

- **Track A (guaranteed):** ship with a pretrained YOLOv8/YOLO11 checkpoint in "proposal mode" (low threshold, class-agnostic) so the end-to-end pipeline always demos. The human-review step is the product; the model is swappable (`MINEMARK_MODEL` env var).
- **Track B (the wow):** fine-tune on open data — Friday/Saturday task, using Codex to write the label-conversion and training scripts:
  - **Baur et al. 2026** seeded-minefield benchmark — 34 open UAV datasets incl. RGB over 143 seeded items. Get download links from the paper's Data Availability section: https://www.mdpi.com/2072-4292/18/13/2182
  - **Demining Research Community** open datasets (PFM-1 "butterfly mine" UAV imagery, thermal + RGB): https://www.de-mine.com/home
  - **UAV VNIR hyperspectral landmine/UXO benchmark** (labels reusable for RGB-adjacent work): https://arxiv.org/abs/2510.02700
  - Roboflow Universe has several small "UXO / landmine" labeled sets — search and pull anything Apache/CC-licensed as augmentation.
  - Train YOLOv8n/s at 640–1024px on a rented GPU (Colab Pro / Lambda, ~$10–30). Even ~500 labeled tiles fine-tunes usefully. Log mAP; report honestly.

---

## 4. Day-by-day schedule

**Thu Jul 17 (today) — skeleton runs end-to-end.**
Repo up on GitHub (public, Apache-2.0). `pip install -e .` works. Upload → tile → pretrained detect → markers on Leaflet map → GeoJSON export, all with dummy-quality detections. Register on Devpost; start dataset downloads overnight.

**Fri Jul 18 — data + training.**
Convert Baur/DRC labels to YOLO format (Codex writes the converters). Kick off fine-tune. Meanwhile: review UI polish (crop viewer, y/n/u keys, progress counter), EXIF→geo math tested against a known image.

**Sat Jul 19 — integrate model + report.**
Drop fine-tuned weights in, measure before/after on a held-out set (this comparison is your best demo moment). Build the HTML survey report + KML export. Write README with architecture diagram.

**Sun Jul 20 — demo video + hardening.**
Record the <3-min video (script below). Fix what recording reveals. Tag v0.1.0. Write Devpost submission text.

**Mon Jul 21 — buffer + submit by noon PT.**
Never submit at 4:55pm PT.

---

## 5. Demo video script (<3 min)

1. **0:00–0:25 — Problem.** One slide: 6,279 casualties in 2024, worst since 2020; the tech that works is proprietary and Ukraine-only. "We open-sourced the missing piece."
2. **0:25–1:45 — Live demo.** Upload real drone imagery → detections appear on map → rapid-fire confirm/reject with keyboard → export GeoJSON → open in QGIS/Google Earth to show it's real georeferenced data → show the survey report with the disclaimer visible.
3. **1:45–2:20 — The model.** Before/after fine-tuning comparison; name the open datasets; "trained on openly published seeded-minefield benchmarks."
4. **2:20–2:50 — Impact + honesty.** Who it's for (accredited operators in low-income countries), what it never does (declare land safe), Apache license, built with Codex throughout.

**Judging criteria mapping:** technical implementation = tiling/georef/fine-tune pipeline; design/UX = keyboard-speed review loop; impact = the whole premise; idea quality = documented gap (cite the research).

---

## 6. Devpost submission checklist

- [ ] Public GitHub repo, Apache-2.0 LICENSE, README with quickstart + screenshots
- [ ] DISCLAIMER.md prominent and linked from README top
- [ ] <3-min demo video (unlisted YouTube)
- [ ] Project description (reuse §1 pitch + impact paragraph)
- [ ] Note Codex usage explicitly (judges look for it) — keep a `docs/codex-log.md` of what Codex built
- [ ] Tag release v0.1.0

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Fine-tune fails / no GPU time | Track A pretrained proposal mode still demos the full product |
| Dataset downloads slow/broken | Start tonight; DRC + Roboflow as fallbacks; worst case, hand-label 100 tiles from any open UAV imagery |
| GeoTIFF/CRS rabbit hole | MVP = EXIF-GPS JPEGs (simple math); GeoTIFF via rasterio only if time |
| Scope creep | Anything not in §2 MVP list waits until Sunday |
| Solo-builder fatigue | The Thursday skeleton is the only hard gate; everything after is additive |

---

## 8. After Build Week (so the week compounds)

Share the repo with the Demining Research Community (they explicitly invite collaboration), GICHD's innovation team, and HI's drone unit. A hackathon win is a nice line in the concept note; a repo an operator actually pilots is the real prize.
