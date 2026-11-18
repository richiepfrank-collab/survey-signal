"""Smoke tests: pipeline math that must not silently break."""
import math

import numpy as np
import pytest

from backend import detector
from backend.detector import Detection, _iou, _nms
from backend.exports import to_geojson
from backend.georef import ImageGeo
from backend.imageio import open_tile_reader


def test_nms_merges_tile_seam_duplicates():
    a = Detection(100, 100, 140, 140, conf=0.9, label="ordnance")
    b = Detection(102, 101, 141, 142, conf=0.7, label="ordnance")  # same object, next tile
    c = Detection(500, 500, 540, 540, conf=0.6, label="ordnance")
    kept = _nms([a, b, c])
    assert len(kept) == 2 and kept[0].conf == 0.9


def test_iou_disjoint_is_zero():
    a = Detection(0, 0, 10, 10, conf=1, label="x")
    b = Detection(100, 100, 110, 110, conf=1, label="x")
    assert _iou(a, b) == 0.0


def test_pixel_to_lonlat_center_and_offset():
    geo = ImageGeo(lat=13.5, lon=104.9, altitude_m=60, width_px=4000, height_px=3000, gsd_m=0.02)
    lon, lat = geo.pixel_to_lonlat(2000, 1500)  # center pixel -> image GPS
    assert math.isclose(lon, 104.9) and math.isclose(lat, 13.5)
    # 1000 px east = 20 m east -> lon increases, lat unchanged
    lon2, lat2 = geo.pixel_to_lonlat(3000, 1500)
    assert lon2 > lon and math.isclose(lat2, lat)


def test_geojson_exports_only_confirmed_by_default():
    dets = [
        {"id": "a", "label": "ordnance", "conf": 0.9, "status": "confirmed",
         "lon": 104.9, "lat": 13.5, "image": "x.jpg"},
        {"id": "b", "label": "ordnance", "conf": 0.8, "status": "rejected",
         "lon": 104.9, "lat": 13.5, "image": "x.jpg"},
    ]
    gj = to_geojson(dets)
    assert len(gj["features"]) == 1 and gj["features"][0]["properties"]["id"] == "a"
    assert "disclaimer" in gj["properties"]


def test_detector_does_not_download_an_unconfigured_model(monkeypatch):
    monkeypatch.setattr(detector, "MODEL_PATH", None)
    monkeypatch.setattr(detector, "_model", None)
    try:
        detector.get_model()
    except RuntimeError as exc:
        assert "No local detector" in str(exc)
    else:
        raise AssertionError("an unconfigured detector must not trigger a download")


def test_geotiff_reader_reads_a_bounded_window(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    source = tmp_path / "tiny.tif"
    pixels = np.zeros((4, 4, 4), dtype=np.uint8)
    pixels[:, :, 0] = 12
    with rasterio.open(
        source, "w", driver="GTiff", width=4, height=4, count=4, dtype="uint8",
        crs="EPSG:4326", transform=from_origin(1, 2, 0.01, 0.01),
    ) as dst:
        dst.write(np.moveaxis(pixels, -1, 0))

    with open_tile_reader(str(source)) as reader:
        tile = reader.read_rgb(1, 1, 2, 2)
    assert tile.shape == (2, 2, 3)
    assert tile[0, 0, 0] == 12


# --- EXIF footprint georeferencing -------------------------------------------

def _gps_jpeg(path, *, gps_alt_m=1500, focal_35=24, xmp=None, size=(400, 300)):
    """Write a JPEG with EXIF GPS (13.5 N, 104.9 E) and an optional DJI-style XMP packet."""
    import piexif
    from PIL import Image

    exif = {
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((13, 1), (30, 1), (0, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"E",
            piexif.GPSIFD.GPSLongitude: ((104, 1), (54, 1), (0, 1)),
            piexif.GPSIFD.GPSAltitude: (gps_alt_m * 10, 10),
        },
        "Exif": {piexif.ExifIFD.FocalLength: (88, 10)},
    }
    if focal_35:
        exif["Exif"][piexif.ExifIFD.FocalLengthIn35mmFilm] = focal_35
    Image.new("RGB", size, (90, 120, 60)).save(path, format="JPEG", exif=piexif.dump(exif))
    if xmp:
        attrs = " ".join(f'drone-dji:{k}="{v}"' for k, v in xmp.items())
        packet = (b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta><rdf:Description "
                  + attrs.encode() + b"/></x:xmpmeta>")
        raw = path.read_bytes()
        segment = b"\xff\xe1" + (len(packet) + 2).to_bytes(2, "big") + packet
        end_of_exif = 4 + int.from_bytes(raw[4:6], "big")  # SOI + first APP1 (EXIF)
        path.write_bytes(raw[:end_of_exif] + segment + raw[end_of_exif:])
    return path


def test_yaw_rotates_pixel_offsets():
    # 100 px above centre at 0.1 m/px is 10 m along the camera heading.
    def offset(yaw):
        geo = ImageGeo(lat=0.0, lon=0.0, altitude_m=50, width_px=1000, height_px=1000,
                       gsd_m=0.1, yaw_deg=yaw)
        lon, lat = geo.pixel_to_lonlat(500, 400)
        metres_per_degree = math.pi * 6_378_137.0 / 180
        return lon * metres_per_degree, lat * metres_per_degree  # east, north

    for yaw, (east, north) in {0: (0, 10), 90: (10, 0), 180: (0, -10), -90: (-10, 0)}.items():
        got_east, got_north = offset(yaw)
        assert math.isclose(got_east, east, abs_tol=1e-6), yaw
        assert math.isclose(got_north, north, abs_tol=1e-6), yaw


def test_relative_altitude_and_yaw_come_from_xmp(tmp_path, monkeypatch):
    from backend import georef

    monkeypatch.delenv("MINEMARK_AGL_M", raising=False)
    path = _gps_jpeg(tmp_path / "dji.jpg", gps_alt_m=1500, xmp={
        "RelativeAltitude": "+40.00", "GimbalYawDegree": "-90.00", "GimbalPitchDegree": "-90.00"})
    geo = georef.extract_geo(str(path))
    assert geo.altitude_m == 40 and geo.altitude_source == "xmp_relative_altitude"
    assert geo.yaw_deg == -90 and geo.yaw_source == "xmp_gimbal_yaw"
    assert geo.warnings == [] and geo.quality == "approximate"
    # 24 mm equivalent at 40 m: the frame diagonal covers 40 * 43.2666 / 24 m of ground.
    assert math.isclose(geo.gsd_m * math.hypot(400, 300), 40 * 43.2666 / 24, rel_tol=1e-9)


def test_sea_level_gps_altitude_is_flagged_not_trusted(tmp_path, monkeypatch):
    from backend import georef

    monkeypatch.delenv("MINEMARK_AGL_M", raising=False)
    path = _gps_jpeg(tmp_path / "plain.jpg", gps_alt_m=1500)
    geo = georef.extract_geo(str(path))
    assert geo.altitude_source == "exif_gps_altitude_above_sea_level"
    assert geo.yaw_source == "assumed_north_up"
    assert geo.quality == "unverified" and len(geo.warnings) == 2

    monkeypatch.setenv("MINEMARK_AGL_M", "35")
    geo = georef.extract_geo(str(path))
    assert geo.altitude_m == 35 and geo.altitude_source == "operator_override"


def test_oblique_gimbal_pitch_is_flagged(tmp_path, monkeypatch):
    from backend import georef

    monkeypatch.delenv("MINEMARK_AGL_M", raising=False)
    path = _gps_jpeg(tmp_path / "oblique.jpg", xmp={
        "RelativeAltitude": "+40.00", "GimbalYawDegree": "10.0", "GimbalPitchDegree": "-45.00"})
    geo = georef.extract_geo(str(path))
    assert geo.quality == "unverified" and "straight down" in geo.warnings[0]


def test_footprint_bounds_enclose_a_rotated_frame():
    from backend.georef import footprint_bounds

    geo = ImageGeo(lat=10.0, lon=20.0, altitude_m=50, width_px=4000, height_px=3000,
                   gsd_m=0.02, yaw_deg=90)
    (south, west), (north, east) = footprint_bounds(geo)
    metres_per_degree = math.pi * 6_378_137.0 / 180
    # Heading east, the 80 m frame width runs north-south and the 60 m height east-west.
    assert math.isclose((north - south) * metres_per_degree, 80, rel_tol=1e-6)
    assert math.isclose((east - west) * metres_per_degree * math.cos(math.radians(10)), 60,
                        rel_tol=1e-6)


# --- persistence and audit trail ----------------------------------------------

def _row(det_id, **over):
    return {"id": det_id, "image_id": "img1", "image": "img1_a.jpg", "x1": 1, "y1": 2, "x2": 3,
            "y2": 4, "conf": 0.5, "label": "object", "status": "pending", "lon": 104.9,
            "lat": 13.5, "position_quality": "approximate", "extra": {}, **over}


def test_store_survives_restart_and_logs_every_decision(tmp_path):
    from backend.store import Store

    db = tmp_path / "session.sqlite3"
    store = Store(db)
    store.add_image({"id": "img1", "file": "img1_a.jpg", "sha256": "ab" * 32, "model": "m",
                     "geo": {"quality": "approximate", "warnings": []},
                     "bounds": [[13.4, 104.8], [13.6, 105.0]]}, [_row("d1"), _row("d2")])
    store.set_status("d1", "confirmed", "analyst-7")
    store.set_status("d1", "rejected", "  ")
    assert store.set_status("missing", "confirmed", "x") is None
    with pytest.raises(ValueError):
        store.set_status("d1", "cleared", "x")

    reopened = Store(db)  # a new process sees the same session
    assert reopened.detection("d1")["status"] == "rejected"
    assert reopened.detection("d2")["status"] == "pending"
    assert reopened.image("img1")["bounds"] == [[13.4, 104.8], [13.6, 105.0]]
    log = reopened.review_log()
    assert [(e["from_status"], e["to_status"], e["analyst"]) for e in log] == [
        ("pending", "confirmed", "analyst-7"), ("confirmed", "rejected", "unspecified")]


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend import app as app_module

    monkeypatch.delenv("MINEMARK_AGL_M", raising=False)
    monkeypatch.delenv("MINEMARK_BASEMAP_URL", raising=False)
    monkeypatch.setattr(detector, "get_model", lambda: None)
    monkeypatch.setattr(detector, "detect_image", lambda path: [
        Detection(190, 140, 210, 160, conf=0.9, label="object"),
        Detection(10, 10, 30, 30, conf=0.4, label="object")])
    original = app_module.DATA_DIR
    app_module.configure(tmp_path / "session")
    yield TestClient(app_module.app)
    app_module.configure(original)


def test_review_workflow_persists_and_exports(client, tmp_path):
    from backend import app as app_module

    jpeg = _gps_jpeg(tmp_path / "frame.jpg", xmp={
        "RelativeAltitude": "+40.00", "GimbalYawDegree": "90.00", "GimbalPitchDegree": "-90.00"})
    with jpeg.open("rb") as handle:
        uploaded = client.post("/api/upload", files={"files": ("frame.jpg", handle, "image/jpeg")})
    assert uploaded.status_code == 200
    image = uploaded.json()["images"][0]
    assert image["geo"]["quality"] == "approximate" and len(image["sha256"]) == 64

    dets = client.get("/api/detections").json()["detections"]
    centre = next(d for d in dets if d["conf"] == 0.9)
    assert math.isclose(centre["lat"], 13.5, abs_tol=1e-9)  # image-centre detection = GPS fix
    assert client.post(f"/api/detections/{centre['id']}/status/confirmed",
                       params={"analyst": "analyst-7"}).status_code == 200

    app_module.configure(app_module.DATA_DIR)  # simulate a server restart
    features = client.get("/api/export/geojson").json()["features"]
    assert [f["properties"]["id"] for f in features] == [centre["id"]]
    assert features[0]["properties"]["reviewed_by"] == "analyst-7"
    assert len(client.get("/api/audit").json()["review_log"]) == 1

    report = client.get("/api/export/report", params={"analyst": "<b>x</b>"}).text
    assert "analyst-7" in report and "<b>x</b>" not in report and "SURVEY-ASSIST OUTPUT ONLY" in report

    # A frame heading east is turned north-up for the map: 400x300 becomes 300x400.
    from PIL import Image
    preview = client.get(f"/api/image/{image['id']}/preview")
    assert preview.headers["content-type"] == "image/png"
    import io
    assert Image.open(io.BytesIO(preview.content)).size == (300, 400)


def test_unverified_positions_are_labelled_in_exports(client, tmp_path):
    jpeg = _gps_jpeg(tmp_path / "plain.jpg", gps_alt_m=1500)
    with jpeg.open("rb") as handle:
        client.post("/api/upload", files={"files": ("plain.jpg", handle, "image/jpeg")})
    det = client.get("/api/detections").json()["detections"][0]
    client.post(f"/api/detections/{det['id']}/status/confirmed")
    feature = client.get("/api/export/geojson").json()["features"][0]
    assert feature["properties"]["position_quality"] == "unverified"
    assert "sea level" in client.get("/api/export/report").text


def test_review_ui_makes_no_external_requests(client):
    import re

    page = client.get("/").text
    assert not re.search(r"""(?:src|href)\s*=\s*["'](?:https?:)?//""", page)
    assert "tile.openstreetmap.org" not in page and "cdnjs" not in page
    assert client.get("/vendor/leaflet/leaflet.js").status_code == 200
    assert client.get("/vendor/leaflet/leaflet.css").status_code == 200
    assert client.get("/api/config").json()["basemap_url"] is None


def test_geotiff_preview_is_decimated_and_masked(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    from backend.imageio import render_preview

    source = tmp_path / "ortho.tif"
    pixels = np.full((4, 600, 400), 200, dtype=np.uint8)
    pixels[3] = 255
    pixels[3, :300, :] = 0  # top half transparent, as in a clipped orthomosaic
    with rasterio.open(source, "w", driver="GTiff", width=400, height=600, count=4,
                       dtype="uint8", crs="EPSG:4326", photometric="RGB", alpha="YES",
                       transform=from_origin(1, 2, 0.0001, 0.0001)) as dst:
        dst.write(pixels)
    preview = render_preview(str(source), max_px=300)
    assert preview.size == (200, 300) and preview.mode == "RGBA"
    assert preview.getpixel((100, 10))[3] == 0 and preview.getpixel((100, 290))[3] == 255
