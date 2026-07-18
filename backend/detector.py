"""Tiled, local-only RT-DETR inference for Survey Signal."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .imageio import open_tile_reader

TILE = 1024
OVERLAP = 128
DEFAULT_CONF = float(os.environ.get("MINEMARK_CONF", "0.15"))
MODEL_PATH = os.environ.get("MINEMARK_MODEL")

_model = None


def get_model():
    """Load an explicitly staged model without allowing network resolution."""
    global _model
    if _model is None:
        if not MODEL_PATH:
            raise RuntimeError(
                "No local detector is configured. Set MINEMARK_MODEL to an approved local model directory."
            )
        if not Path(MODEL_PATH).is_dir():
            raise RuntimeError(f"Configured model does not exist: {MODEL_PATH}")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

        processor = RTDetrImageProcessor.from_pretrained(MODEL_PATH, local_files_only=True)
        model = RTDetrForObjectDetection.from_pretrained(MODEL_PATH, local_files_only=True)
        model.eval()
        _model = (processor, model, torch)
    return _model


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    label: str
    id: str = ""
    status: str = "pending"
    lon: float | None = None
    lat: float | None = None
    extra: dict = field(default_factory=dict)

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2


def _iou(a: Detection, b: Detection) -> float:
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    return inter / (area_a + area_b - inter)


def _nms(dets: list[Detection], iou_thr: float = 0.5) -> list[Detection]:
    dets = sorted(dets, key=lambda d: d.conf, reverse=True)
    kept: list[Detection] = []
    for d in dets:
        if all(_iou(d, k) < iou_thr for k in kept):
            kept.append(d)
    return kept


def detect_image(image_path: str, conf: float = DEFAULT_CONF) -> list[Detection]:
    """Detect each bounded image tile and return full-image pixel coordinates."""
    processor, model, torch = get_model()
    with open_tile_reader(image_path) as image:
        step = TILE - OVERLAP
        dets: list[Detection] = []
        xs = list(range(0, max(image.width - OVERLAP, 1), step)) or [0]
        ys = list(range(0, max(image.height - OVERLAP, 1), step)) or [0]
        for ty in ys:
            for tx in xs:
                tile = image.read_rgb(tx, ty, TILE, TILE)
                if tile.size == 0:
                    continue
                inputs = processor(images=tile, return_tensors="pt")
                with torch.inference_mode():
                    outputs = model(**inputs)
                target_sizes = torch.tensor([[tile.shape[0], tile.shape[1]]])
                result = processor.post_process_object_detection(
                    outputs, target_sizes=target_sizes, threshold=conf
                )[0]
                for box, score, label_id in zip(
                    result["boxes"], result["scores"], result["labels"], strict=True
                ):
                    x1, y1, x2, y2 = box.tolist()
                    label_index = int(label_id)
                    dets.append(
                        Detection(
                            x1=x1 + tx, y1=y1 + ty, x2=x2 + tx, y2=y2 + ty,
                            conf=float(score),
                            label=model.config.id2label[label_index],
                        )
                    )
    return _nms(dets)
