"""Pixel -> WGS84 georeferencing.

GeoTIFF path (optional extra): rasterio affine transform, exact per-pixel CRS.

EXIF path: GPS-tagged nadir JPEGs. The ground footprint is derived from the
image-centre GPS fix, the height above ground, the lens field of view, and the
camera heading. Each input is taken from the most trustworthy source present
and the source is recorded, because a wrong assumption here moves markers:

* Height above ground: ``MINEMARK_AGL_M`` operator override, then the DJI XMP
  ``RelativeAltitude`` (height above the take-off point). EXIF ``GPSAltitude``
  is height above sea level, not above ground; it is used only as a last
  resort and flags the image's positions as unverified.
* Heading: XMP gimbal/flight yaw, then EXIF ``GPSImgDirection``. Without one
  the image is assumed north-up and flagged.
* Field of view: EXIF 35 mm-equivalent focal length, else focal length with an
  assumed sensor width (flagged).

This is survey-assist accuracy (metres), NOT surveying-grade.
"""
from __future__ import annotations

import math
import os
import re
import struct
from dataclasses import dataclass, field

import piexif
from PIL import Image

EARTH_RADIUS_M = 6_378_137.0
FULL_FRAME_DIAGONAL_MM = 43.2666  # 36 x 24 mm reference frame

# Fallbacks, used only when the image carries no better information.
DEFAULT_SENSOR_WIDTH_MM = 13.2  # 1" sensor (Mavic 3E / Phantom 4 Pro class)
DEFAULT_FOCAL_MM = 8.8
DEFAULT_ALTITUDE_M = 60.0

NADIR_PITCH_TOLERANCE_DEG = 10.0
_XMP_SCAN_BYTES = 1 << 20

QUALITY_GEOREFERENCED = "georeferenced"  # GeoTIFF affine transform
QUALITY_APPROXIMATE = "approximate"      # EXIF footprint, every input measured
QUALITY_UNVERIFIED = "unverified"        # EXIF footprint, at least one input assumed


@dataclass
class ImageGeo:
    lat: float
    lon: float
    altitude_m: float  # height above ground used for the footprint
    width_px: int
    height_px: int
    gsd_m: float  # ground sample distance, meters/pixel
    yaw_deg: float = 0.0  # compass heading of the image's top edge, clockwise from north
    altitude_source: str = "unspecified"
    yaw_source: str = "unspecified"
    gsd_source: str = "unspecified"
    warnings: list[str] = field(default_factory=list)

    @property
    def quality(self) -> str:
        return QUALITY_UNVERIFIED if self.warnings else QUALITY_APPROXIMATE

    def pixel_to_lonlat(self, px: float, py: float) -> tuple[float, float]:
        """Offset from image centre in pixels -> WGS84 lon/lat (nadir assumption)."""
        right_m = (px - self.width_px / 2) * self.gsd_m
        up_m = -(py - self.height_px / 2) * self.gsd_m  # image y grows downward
        yaw = math.radians(self.yaw_deg)
        east_m = right_m * math.cos(yaw) + up_m * math.sin(yaw)
        north_m = -right_m * math.sin(yaw) + up_m * math.cos(yaw)
        dlat = north_m / EARTH_RADIUS_M * (180 / math.pi)
        dlon = east_m / (EARTH_RADIUS_M * math.cos(math.radians(self.lat))) * (180 / math.pi)
        return self.lon + dlon, self.lat + dlat

    def describe(self) -> dict:
        return {
            "method": "exif_footprint", "quality": self.quality,
            "altitude_agl_m": round(self.altitude_m, 2), "altitude_source": self.altitude_source,
            "yaw_deg": round(self.yaw_deg, 2), "yaw_source": self.yaw_source,
            "gsd_m": self.gsd_m, "gsd_source": self.gsd_source,
            "warnings": list(self.warnings),
        }


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
    yaw_deg: float = 0.0
    warnings: list[str] = field(default_factory=list)

    quality = QUALITY_GEOREFERENCED

    def pixel_to_lonlat(self, px: float, py: float) -> tuple[float, float]:
        x, y = self.transform * (px, py)
        lon, lat = self.to_wgs84.transform(x, y)
        return lon, lat

    def describe(self) -> dict:
        return {"method": "geotiff_transform", "quality": self.quality, "gsd_m": self.gsd_m,
                "warnings": list(self.warnings)}


def footprint_bounds(geo: ImageGeo | GeoTiffGeo) -> list[list[float]]:
    """[[south, west], [north, east]] box enclosing the image's four corners."""
    corners = [geo.pixel_to_lonlat(x, y) for x in (0, geo.width_px) for y in (0, geo.height_px)]
    lons, lats = [c[0] for c in corners], [c[1] for c in corners]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def _dms_to_deg(dms, ref) -> float:
    deg = dms[0][0] / dms[0][1] + dms[1][0] / dms[1][1] / 60 + dms[2][0] / dms[2][1] / 3600
    return -deg if ref in (b"S", b"W", "S", "W") else deg


def _rational(value) -> float | None:
    if not value or not value[1]:
        return None
    return value[0] / value[1]


def _read_xmp_numbers(image_path: str) -> dict[str, float]:
    """Pull the DJI flight-geometry values out of a JPEG's XMP packet, if any."""
    with open(image_path, "rb") as handle:
        head = handle.read(_XMP_SCAN_BYTES)
    found: dict[str, float] = {}
    for key in ("RelativeAltitude", "GimbalYawDegree", "GimbalPitchDegree", "FlightYawDegree"):
        # Values appear as attributes (key="+12.3") or as elements (<key>+12.3</key>).
        pattern = rb"drone-dji:" + key.encode() + rb"\s*(?:=\s*\"|>)\s*([+-]?\d+(?:\.\d+)?)"
        match = re.search(pattern, head)
        if match:
            found[key] = float(match.group(1))
    return found


def _operator_agl_override() -> float | None:
    raw = os.environ.get("MINEMARK_AGL_M")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"MINEMARK_AGL_M must be a number of metres, got {raw!r}") from exc
    if value <= 0:
        raise RuntimeError("MINEMARK_AGL_M must be greater than zero")
    return value


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
    """Read EXIF GPS + camera geometry; return None if the image has no GPS."""
    if image_path.lower().endswith((".tif", ".tiff")):
        return _extract_geotiff_geo(image_path)

    with Image.open(image_path) as img:
        w, h = img.size
    try:
        exif = piexif.load(image_path)
    except (piexif.InvalidImageDataError, ValueError, KeyError, IndexError, struct.error, OSError):
        return None  # not a JPEG/TIFF, or unreadable EXIF: treat as an image with no GPS
    gps = exif.get("GPS") or {}
    if piexif.GPSIFD.GPSLatitude not in gps or piexif.GPSIFD.GPSLongitude not in gps:
        return None
    lat = _dms_to_deg(gps[piexif.GPSIFD.GPSLatitude], gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N"))
    lon = _dms_to_deg(gps[piexif.GPSIFD.GPSLongitude], gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E"))
    xmp = _read_xmp_numbers(image_path)
    warnings: list[str] = []

    # --- height above ground -------------------------------------------------
    override = _operator_agl_override()
    gps_alt = _rational(gps.get(piexif.GPSIFD.GPSAltitude))
    if override is not None:
        alt, alt_source = override, "operator_override"
    elif xmp.get("RelativeAltitude", 0) > 0:
        alt, alt_source = xmp["RelativeAltitude"], "xmp_relative_altitude"
    elif gps_alt is not None and gps_alt > 0:
        alt, alt_source = gps_alt, "exif_gps_altitude_above_sea_level"
        warnings.append(
            "Height above ground is unknown: EXIF GPS altitude is measured from sea level, so "
            "marker offsets from the image centre are unreliable. Set MINEMARK_AGL_M to the "
            "flight height above ground."
        )
    else:
        alt, alt_source = DEFAULT_ALTITUDE_M, "assumed_default"
        warnings.append(
            f"No altitude in the image: assumed {DEFAULT_ALTITUDE_M:.0f} m above ground. "
            "Set MINEMARK_AGL_M to the flight height above ground."
        )

    # --- heading of the image's top edge -------------------------------------
    img_direction = _rational(gps.get(piexif.GPSIFD.GPSImgDirection))
    if "GimbalYawDegree" in xmp:
        yaw, yaw_source = xmp["GimbalYawDegree"], "xmp_gimbal_yaw"
    elif "FlightYawDegree" in xmp:
        yaw, yaw_source = xmp["FlightYawDegree"], "xmp_flight_yaw"
    elif img_direction is not None:
        yaw, yaw_source = img_direction, "exif_gps_img_direction"
    else:
        yaw, yaw_source = 0.0, "assumed_north_up"
        warnings.append(
            "Camera heading is unknown: the image is assumed north-up, so markers may be "
            "rotated about the image centre."
        )

    pitch = xmp.get("GimbalPitchDegree")
    if pitch is not None and abs(pitch + 90) > NADIR_PITCH_TOLERANCE_DEG:
        warnings.append(
            f"Camera was not pointing straight down (gimbal pitch {pitch:.0f}°): the nadir "
            "footprint model does not hold for this image."
        )

    # --- ground sample distance ----------------------------------------------
    exif_ifd = exif.get("Exif") or {}
    focal_35 = exif_ifd.get(piexif.ExifIFD.FocalLengthIn35mmFilm)
    focal_mm = _rational(exif_ifd.get(piexif.ExifIFD.FocalLength))
    if focal_35:
        # 35 mm equivalence is defined on the frame diagonal, so no sensor size is needed.
        gsd = alt * FULL_FRAME_DIAGONAL_MM / (focal_35 * math.hypot(w, h))
        gsd_source = "exif_35mm_equivalent_focal_length"
    else:
        gsd = DEFAULT_SENSOR_WIDTH_MM * alt / ((focal_mm or DEFAULT_FOCAL_MM) * w)
        gsd_source = "assumed_sensor_width"
        warnings.append(
            f"Lens field of view is partly assumed (sensor width {DEFAULT_SENSOR_WIDTH_MM} mm"
            + ("" if focal_mm else f", focal length {DEFAULT_FOCAL_MM} mm")
            + "): marker offsets scale with this assumption."
        )

    return ImageGeo(lat=lat, lon=lon, altitude_m=alt, width_px=w, height_px=h, gsd_m=gsd,
                    yaw_deg=yaw, altitude_source=alt_source, yaw_source=yaw_source,
                    gsd_source=gsd_source, warnings=warnings)
