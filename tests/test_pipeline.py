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
