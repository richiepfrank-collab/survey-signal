# Open datasets for training

No data ships in this repo. All sources below are openly published; check each license before redistribution.

For the locally staged DRC demo orthomosaic, its exact source, license,
checksum, and training-label status are recorded in [DRC_PROVENANCE.md](DRC_PROVENANCE.md).

**1. Baur et al. 2026 — seeded-minefield UAV benchmark (the best starting point).**
34 open multimodal UAV/geophysical datasets over a 143-item seeded test field, including RGB with ground truth. Follow the *Data Availability* section of the paper for the archive links and interactive web map: https://www.mdpi.com/2072-4292/18/13/2182

**2. Demining Research Community — open PFM-1 ("butterfly mine") datasets.**
UAV RGB + thermal imagery with labels from the Binghamton University group's published studies: https://www.de-mine.com/home (see Publications/Datasets).

**3. UAV VNIR hyperspectral landmine/UXO benchmark** (labels/geometry reusable): https://arxiv.org/abs/2510.02700

**4. Roboflow Universe** — search "UXO", "landmine", "ordnance"; several small community-labeled sets exist. Verify licenses; use as augmentation only.

## Workflow

```bash
# after downloading a source into data/raw/<name>/
python scripts/prepare_labels.py --source data/raw/<name> --out data/yolo
# Fine-tuning is intentionally gated until object-level DRC labels are verified.
MINEMARK_MODEL=models/rtdetr-r18vd minemark serve
```

Keep a held-out test split from a *different* flight/site than training — same-site splits wildly overstate performance, and honest metrics are the credibility of this project.
