"""Survey Signal FastAPI backend.

Session state (imagery metadata, detections, and the review audit log) lives
in a SQLite file inside the session directory, so review work survives a
restart. Set ``MINEMARK_SESSION`` to keep separate surveys in separate
directories.
"""
from __future__ import annotations

import hashlib
import io
import os
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

from . import detector, exports, georef, imageio
from .store import STATUSES, Store

app = FastAPI(title="Survey Signal", version="0.1.0")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
FRONTEND = FRONTEND_DIR / "index.html"
app.mount("/vendor", StaticFiles(directory=FRONTEND_DIR / "vendor"), name="vendor")

DATA_DIR: Path
IMG_DIR: Path
PREVIEW_DIR: Path
STORE: Store


def configure(session_dir: str | Path) -> None:
    """Point the app at a session directory, creating it if needed."""
    global DATA_DIR, IMG_DIR, PREVIEW_DIR, STORE
    DATA_DIR = Path(session_dir)
    IMG_DIR = DATA_DIR / "images"
    PREVIEW_DIR = DATA_DIR / "previews"
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    STORE = Store(DATA_DIR / "session.sqlite3")


configure(os.environ.get("MINEMARK_SESSION", "minemark_session"))


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND.read_text(encoding="utf-8")


@app.get("/api/config")
def config():
    """Runtime options for the review UI. The basemap is off unless an operator opts in."""
    return {
        "model": detector.MODEL_PATH,
        "basemap_url": os.environ.get("MINEMARK_BASEMAP_URL") or None,
        "basemap_attribution": os.environ.get("MINEMARK_BASEMAP_ATTRIBUTION", ""),
    }


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
        digest = hashlib.sha256()
        with dest.open("wb") as out:
            while chunk := f.file.read(1 << 20):
                digest.update(chunk)
                out.write(chunk)

        try:
            geo = georef.extract_geo(str(dest))
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        rows = []
        for d in detector.detect_image(str(dest)):
            d.id = uuid.uuid4().hex[:8]
            if geo:
                d.lon, d.lat = geo.pixel_to_lonlat(d.cx, d.cy)
            rows.append({**asdict(d), "image": dest.name, "image_id": image_id,
                         "position_quality": geo.quality if geo else None})

        results.append(STORE.add_image({
            "id": image_id, "file": dest.name, "sha256": digest.hexdigest(),
            "model": detector.MODEL_PATH,
            "lat": geo.lat if geo else None, "lon": geo.lon if geo else None,
            "gsd_m": geo.gsd_m if geo else None,
            "geo": geo.describe() if geo else None,
            "bounds": georef.footprint_bounds(geo) if geo else None,
        }, rows))
    return {"images": results, "total_detections": len(STORE.detections())}


@app.get("/api/images")
def images():
    return {"images": STORE.images()}


@app.get("/api/detections")
def detections():
    return {"detections": STORE.detections(), "model": detector.MODEL_PATH}


@app.post("/api/detections/{det_id}/status/{status}")
def set_status(det_id: str, status: str, analyst: str = "unspecified"):
    if status not in STATUSES:
        return JSONResponse({"error": "bad status"}, status_code=400)
    updated = STORE.set_status(det_id, status, analyst)
    if updated is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return updated


@app.get("/api/audit")
def audit():
    """Every review decision in the order it was made."""
    return {"review_log": STORE.review_log()}


@app.get("/api/crop/{det_id}")
def crop(det_id: str, pad: int = 64):
    d = STORE.detection(det_id)
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
    gj = exports.to_geojson(STORE.detections(), statuses)
    return Response(exports.dumps(gj), media_type="application/geo+json",
                    headers={"Content-Disposition": "attachment; filename=minemark_hazards.geojson"})


@app.get("/api/export/kml")
def export_kml(include_unsure: bool = False):
    statuses = ("confirmed", "unsure") if include_unsure else ("confirmed",)
    kml = exports.to_kml(STORE.detections(), statuses)
    return Response(kml, media_type="application/vnd.google-earth.kml+xml",
                    headers={"Content-Disposition": "attachment; filename=minemark_hazards.kml"})


@app.get("/api/export/report")
def export_report(analyst: str = "unspecified"):
    html = exports.to_report_html(STORE.detections(), detector.MODEL_PATH, len(STORE.images()),
                                  analyst, images=STORE.images())
    return HTMLResponse(html)


@app.get("/api/image/{image_id}")
def image(image_id: str):
    meta = STORE.image(image_id)
    if not meta:
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(IMG_DIR / meta["file"])


@app.get("/api/image/{image_id}/preview")
def image_preview(image_id: str):
    """North-up overview of an image, drawn under the markers in place of a web basemap."""
    meta = STORE.image(image_id)
    if not meta:
        return JSONResponse({"error": "not found"}, status_code=404)
    cached = PREVIEW_DIR / f"{image_id}.png"
    if not cached.exists():
        yaw = (meta["geo"] or {}).get("yaw_deg") or 0.0
        preview = imageio.render_preview(str(IMG_DIR / meta["file"]), rotate_cw_deg=yaw)
        partial = cached.with_suffix(".partial")
        preview.save(partial, format="PNG")
        partial.replace(cached)
    return FileResponse(cached, media_type="image/png")
