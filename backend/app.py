"""Survey Signal FastAPI backend.

In-memory session store (hackathon MVP): one global project, detections keyed
by id. State is lost on restart — export early, export often.
"""
from __future__ import annotations

import io
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from PIL import Image

from . import detector, exports, georef, imageio

app = FastAPI(title="Survey Signal", version="0.1.0")

DATA_DIR = Path("minemark_session")
IMG_DIR = DATA_DIR / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

STATE: dict = {"images": {}, "detections": {}}  # image_id -> meta ; det_id -> det dict
FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND.read_text()


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    """Store supported imagery and add its AI proposals to the review queue."""
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one image.")
    try:
        detector.get_model()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    results = []
    for f in files:
        # ``UploadFile.filename`` is user-controlled; keep uploads inside IMG_DIR.
        filename = Path(f.filename or "upload").name
        if Path(filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported image type: {filename}. Use JPEG, PNG, or GeoTIFF.",
            )
        image_id = uuid.uuid4().hex[:8]
        dest = IMG_DIR / f"{image_id}_{filename}"
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)

        geo = georef.extract_geo(str(dest))
        dets = detector.detect_image(str(dest))
        for d in dets:
            d.id = uuid.uuid4().hex[:8]
            if geo:
                d.lon, d.lat = geo.pixel_to_lonlat(d.cx, d.cy)
            STATE["detections"][d.id] = {**asdict(d), "image": dest.name, "image_id": image_id}

        STATE["images"][image_id] = {
            "id": image_id, "file": dest.name, "n_detections": len(dets),
            "lat": geo.lat if geo else None, "lon": geo.lon if geo else None,
            "gsd_m": geo.gsd_m if geo else None,
        }
        results.append(STATE["images"][image_id])
    return {"images": results, "total_detections": len(STATE["detections"])}


@app.get("/api/detections")
def detections():
    return {"detections": list(STATE["detections"].values()),
            "model": detector.MODEL_PATH}


@app.post("/api/detections/{det_id}/status/{status}")
def set_status(det_id: str, status: str):
    if status not in ("confirmed", "rejected", "unsure", "pending"):
        return JSONResponse({"error": "bad status"}, status_code=400)
    if det_id not in STATE["detections"]:
        return JSONResponse({"error": "not found"}, status_code=404)
    STATE["detections"][det_id]["status"] = status
    return STATE["detections"][det_id]


@app.get("/api/crop/{det_id}")
def crop(det_id: str, pad: int = 64):
    d = STATE["detections"].get(det_id)
    if not d:
        return JSONResponse({"error": "not found"}, status_code=404)
    x1, y1 = max(0, int(d["x1"]) - pad), max(0, int(d["y1"]) - pad)
    x2, y2 = int(d["x2"]) + pad, int(d["y2"]) + pad
    with imageio.open_tile_reader(str(IMG_DIR / d["image"])) as image:
        pixels = image.read_rgb(x1, y1, x2 - x1, y2 - y1)
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", quality=90)
    return Response(buf.getvalue(), media_type="image/jpeg")


@app.get("/api/export/geojson")
def export_geojson(include_unsure: bool = False):
    statuses = ("confirmed", "unsure") if include_unsure else ("confirmed",)
    gj = exports.to_geojson(list(STATE["detections"].values()), statuses)
    return Response(exports.dumps(gj), media_type="application/geo+json",
                    headers={"Content-Disposition": "attachment; filename=minemark_hazards.geojson"})


@app.get("/api/export/kml")
def export_kml(include_unsure: bool = False):
    statuses = ("confirmed", "unsure") if include_unsure else ("confirmed",)
    kml = exports.to_kml(list(STATE["detections"].values()), statuses)
    return Response(kml, media_type="application/vnd.google-earth.kml+xml",
                    headers={"Content-Disposition": "attachment; filename=minemark_hazards.kml"})


@app.get("/api/export/report")
def export_report(analyst: str = "unspecified"):
    html = exports.to_report_html(list(STATE["detections"].values()),
                                  detector.MODEL_PATH, len(STATE["images"]), analyst)
    return HTMLResponse(html)


@app.get("/api/image/{image_id}")
def image(image_id: str):
    meta = STATE["images"].get(image_id)
    if not meta:
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(IMG_DIR / meta["file"])
