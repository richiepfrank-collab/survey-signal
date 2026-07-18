"""Bounded-window image reads for Survey Signal's tiled detection and crop APIs."""
from __future__ import annotations

import warnings
from contextlib import AbstractContextManager
from pathlib import Path

import numpy as np
from PIL import Image

GEOTIFF_SUFFIXES = {".tif", ".tiff"}


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
        if data.shape[0] == 1:
            data = np.repeat(data, 3, axis=0)
        elif data.shape[0] == 2:
            data = np.concatenate((data, data[1:2]), axis=0)
        data = np.moveaxis(data, 0, -1)
        if data.dtype != np.uint8:
            max_value = np.iinfo(data.dtype).max if np.issubdtype(data.dtype, np.integer) else 1.0
            data = np.clip(data.astype(np.float32) * (255 / max_value), 0, 255).astype(np.uint8)
        return data

    def close(self) -> None:
        self._source.close()


def open_tile_reader(image_path: str) -> TileReader:
    if Path(image_path).suffix.lower() in GEOTIFF_SUFFIXES:
        return GeoTiffTileReader(image_path)
    return PillowTileReader(image_path)
