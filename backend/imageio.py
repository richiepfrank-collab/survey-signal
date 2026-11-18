"""Bounded-window image reads for Survey Signal's tiled detection and crop APIs."""
from __future__ import annotations

import warnings
from contextlib import AbstractContextManager
from pathlib import Path

import numpy as np
from PIL import Image

GEOTIFF_SUFFIXES = {".tif", ".tiff"}


def _bands_to_rgb8(data: np.ndarray) -> np.ndarray:
    """(bands, rows, cols) raster block -> (rows, cols, 3) uint8."""
    if data.shape[0] == 1:
        data = np.repeat(data, 3, axis=0)
    elif data.shape[0] == 2:
        data = np.concatenate((data, data[1:2]), axis=0)
    data = np.moveaxis(data, 0, -1)
    if data.dtype != np.uint8:
        max_value = np.iinfo(data.dtype).max if np.issubdtype(data.dtype, np.integer) else 1.0
        data = np.clip(data.astype(np.float32) * (255 / max_value), 0, 255).astype(np.uint8)
    return data


class TileReader(AbstractContextManager):
    """Read RGB regions without materializing an entire orthomosaic."""

    width: int
    height: int

    def read_rgb(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


class PillowTileReader(TileReader):
    def __init__(self, image_path: str):
        # Treat Pillow's decompression warning as an error. Very large imagery
        # must be supplied as a GeoTIFF so rasterio can perform bounded reads.
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            self._image = Image.open(image_path)
        self.width, self.height = self._image.size

    def read_rgb(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        box = (x, y, min(self.width, x + width), min(self.height, y + height))
        return np.asarray(self._image.crop(box).convert("RGB"))

    def close(self) -> None:
        self._image.close()


class GeoTiffTileReader(TileReader):
    def __init__(self, image_path: str):
        try:
            import rasterio
        except ImportError as exc:
            raise RuntimeError(
                "GeoTIFF support requires the optional dependency: pip install -e '.[geotiff]'"
            ) from exc
        self._rasterio = rasterio
        self._source = rasterio.open(image_path)
        self.width, self.height = self._source.width, self._source.height
        if self._source.count < 1:
            self.close()
            raise ValueError("GeoTIFF has no raster bands")

    def read_rgb(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        window = self._rasterio.windows.Window(x, y, width, height)
        indexes = list(range(1, min(self._source.count, 3) + 1))
        data = self._source.read(indexes=indexes, window=window, boundless=False)
        return _bands_to_rgb8(data)

    def close(self) -> None:
        self._source.close()


def open_tile_reader(image_path: str) -> TileReader:
    if Path(image_path).suffix.lower() in GEOTIFF_SUFFIXES:
        return GeoTiffTileReader(image_path)
    return PillowTileReader(image_path)


def render_preview(image_path: str, max_px: int = 2048, rotate_cw_deg: float = 0.0) -> Image.Image:
    """Downsampled RGBA overview of an image, for use as the review map's backdrop.

    GeoTIFFs are read decimated, so a multi-hundred-megapixel orthomosaic never
    has to fit in memory; areas outside the raster's valid mask are transparent.
    ``rotate_cw_deg`` turns a camera frame so that north is up.
    """
    if Path(image_path).suffix.lower() in GEOTIFF_SUFFIXES:
        try:
            import rasterio
        except ImportError as exc:
            raise RuntimeError(
                "GeoTIFF support requires the optional dependency: pip install -e '.[geotiff]'"
            ) from exc
        with rasterio.open(image_path) as src:
            scale = min(1.0, max_px / max(src.width, src.height))
            rows, cols = max(1, round(src.height * scale)), max(1, round(src.width * scale))
            indexes = list(range(1, min(src.count, 3) + 1))
            rgb = _bands_to_rgb8(src.read(indexes=indexes, out_shape=(len(indexes), rows, cols)))
            alpha = src.dataset_mask(out_shape=(rows, cols))
        preview = Image.fromarray(np.dstack((rgb, alpha)))
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(image_path) as image:
                image.thumbnail((max_px, max_px))
                preview = image.convert("RGBA")
    if rotate_cw_deg % 360:
        # Pillow rotates counter-clockwise; the expanded corners stay transparent.
        preview = preview.rotate(-rotate_cw_deg, resample=Image.Resampling.BICUBIC, expand=True)
    return preview
