"""Pixel -> WGS84 georeferencing.

MVP path: GPS-tagged nadir JPEGs. We approximate ground footprint from EXIF
(lat/lon, relative altitude, focal length, sensor width) assuming a nadir shot
aligned north-up unless gimbal yaw is available. This is survey-assist accuracy
(meters), NOT surveying-grade — good enough to put a marker on a map for a
human to investigate, and honest about it.

GeoTIFF path (optional extra): rasterio affine transform, exact per-pixel CRS.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import piexif
from PIL import Image

EARTH_RADIUS_M = 6_378_137.0

# Sensor width fallback (mm) for common survey drones; override per-camera as needed.
DEFAULT_SENSOR_WIDTH_MM = 13.2  # 1" sensor (Mavic 3E / Phantom 4 Pro class)
DEFAULT_FOCAL_MM = 8.8
DEFAULT_ALTITUDE_M = 60.0


@dataclass
class ImageGeo:
    lat: float
    lon: float
    altitude_m: float
    width_px: int
    height_px: int
    gsd_m: float  # ground sample distance, meters/pixel

    def pixel_to_lonlat(self, px: float, py: float) -> tuple[float, float]:
        """Offset from image center in pixels -> WGS84 lon/lat (north-up nadir assumption)."""
        dx_m = (px - self.width_px / 2) * self.gsd_m   # east
        dy_m = (py - self.height_px / 2) * self.gsd_m  # south (image y grows downward)
        dlat = -dy_m / EARTH_RADIUS_M * (180 / math.pi)
        dlon = dx_m / (EARTH_RADIUS_M * math.cos(math.radians(self.lat))) * (180 / math.pi)
        return self.lon + dlon, self.lat + dlat


@dataclass
class GeoTiffGeo:
    """Exact pixel georeferencing supplied by a GeoTIFF affine transform."""

    transform: object
    to_wgs84: object
    width_px: int
    height_px: int
    gsd_m: float | None = None
    lat: float | None = None
    lon: float | None = None

    def pixel_to_lonlat(self, px: float, py: float) -> tuple[float, float]:
        x, y = self.transform * (px, py)
        lon, lat = self.to_wgs84.transform(x, y)
        return lon, lat


def _dms_to_deg(dms, ref) -> float:
    deg = dms[0][0] / dms[0][1] + dms[1][0] / dms[1][1] / 60 + dms[2][0] / dms[2][1] / 3600
    return -deg if ref in (b"S", b"W", "S", "W") else deg


def _extract_geotiff_geo(image_path: str) -> GeoTiffGeo | None:
    """Read a georeferenced TIFF, returning None for ordinary TIFFs."""
    try:
        import rasterio
        from pyproj import Transformer
    except ImportError as exc:
        raise RuntimeError(
            "GeoTIFF support requires the optional dependency: pip install -e '.[geotiff]'"
        ) from exc

    with rasterio.open(image_path) as src:
        if src.crs is None or src.transform.is_identity:
            return None
        to_wgs84 = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
        center_x, center_y = src.transform * (src.width / 2, src.height / 2)
        lon, lat = to_wgs84.transform(center_x, center_y)
        gsd_m = abs(src.transform.a) if src.crs.is_projected else None
        return GeoTiffGeo(src.transform, to_wgs84, src.width, src.height, gsd_m, lat, lon)


def extract_geo(image_path: str) -> ImageGeo | GeoTiffGeo | None:
    """Read EXIF GPS + camera params; return None if the image has no GPS."""
    if image_path.lower().endswith((".tif", ".tiff")):
        return _extract_geotiff_geo(image_path)

    img = Image.open(image_path)
    w, h = img.size
    try:
        exif = piexif.load(image_path)
    except Exception:
        return None
    gps = exif.get("GPS") or {}
    if piexif.GPSIFD.GPSLatitude not in gps:
        return None
    lat = _dms_to_deg(gps[piexif.GPSIFD.GPSLatitude], gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N"))
    lon = _dms_to_deg(gps[piexif.GPSIFD.GPSLongitude], gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E"))

    alt = DEFAULT_ALTITUDE_M
    if piexif.GPSIFD.GPSAltitude in gps:
        num, den = gps[piexif.GPSIFD.GPSAltitude]
        if den:
            alt = num / den

    focal_mm = DEFAULT_FOCAL_MM
    fl = (exif.get("Exif") or {}).get(piexif.ExifIFD.FocalLength)
    if fl and fl[1]:
        focal_mm = fl[0] / fl[1]

    # GSD (m/px) = sensor_width * altitude / (focal * image_width)
    gsd = (DEFAULT_SENSOR_WIDTH_MM / 1000) * alt / ((focal_mm / 1000) * w)
    return ImageGeo(lat=lat, lon=lon, altitude_m=alt, width_px=w, height_px=h, gsd_m=gsd)
