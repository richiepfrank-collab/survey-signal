"""Convert source dataset annotations to YOLO format.

Each open dataset ships different annotation formats (CSV point labels,
COCO JSON, VOC XML). This script is the adapter layer: add a loader per
source, emit YOLO txt labels + dataset.yaml.

Hackathon note: point Codex at a sample of the downloaded annotations and ask
it to fill in the matching loader — that's a 10-minute job per format.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

CLASSES = ["ordnance"]  # single-class MVP: anything explosive-looking is one class


def load_coco(source: Path) -> list[dict]:
    """COCO-format instances.json -> [{image, w, h, boxes:[(x,y,w,h)]}]"""
    ann_file = next(source.rglob("*.json"))
    coco = json.loads(ann_file.read_text())
    images = {im["id"]: im for im in coco["images"]}
    out: dict[int, dict] = {}
    for a in coco["annotations"]:
        im = images[a["image_id"]]
        rec = out.setdefault(a["image_id"], {
            "image": source / im["file_name"], "w": im["width"], "h": im["height"], "boxes": []})
        rec["boxes"].append(a["bbox"])  # COCO xywh
    return list(out.values())


LOADERS = {"coco": load_coco}
# TODO: add "csv_points" (point labels -> fixed-size boxes) and "voc" loaders per dataset.


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--format", default="coco", choices=LOADERS)
    p.add_argument("--val-frac", type=float, default=0.2)
    args = p.parse_args()

    records = LOADERS[args.format](args.source)
    random.Random(42).shuffle(records)
    n_val = int(len(records) * args.val_frac)

    for split, recs in [("val", records[:n_val]), ("train", records[n_val:])]:
        img_dir = args.out / "images" / split
        lbl_dir = args.out / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)
        for r in recs:
            src = Path(r["image"])
            if not src.exists():
                continue
            shutil.copy(src, img_dir / src.name)
            lines = []
            for (x, y, w, h) in r["boxes"]:
                cx, cy = (x + w / 2) / r["w"], (y + h / 2) / r["h"]
                lines.append(f"0 {cx:.6f} {cy:.6f} {w / r['w']:.6f} {h / r['h']:.6f}")
            (lbl_dir / (src.stem + ".txt")).write_text("\n".join(lines))

    (args.out / "dataset.yaml").write_text(
        f"path: {args.out.resolve()}\ntrain: images/train\nval: images/val\n"
        f"names:\n  0: {CLASSES[0]}\n")
    print(f"Wrote {len(records)} records -> {args.out} (val={n_val})")


if __name__ == "__main__":
    main()
