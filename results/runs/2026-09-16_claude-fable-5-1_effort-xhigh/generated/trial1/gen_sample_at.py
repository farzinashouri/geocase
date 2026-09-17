"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
import os
from typing import Optional, Union

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.io import DatasetReader
from rasterio.windows import Window

PathLike = Union[str, "os.PathLike[str]"]

_WGS84 = CRS.from_epsg(4326)


def sample_at(raster_path: PathLike, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at ``(lon, lat)``, or ``None`` if there is no data there.

    ``lon`` and ``lat`` are WGS84 geographic coordinates in decimal degrees.
    They are reprojected into the raster's own coordinate reference system
    before lookup, so the GeoTIFF may use any CRS. If the raster carries no
    CRS at all, the coordinates are used as-is.

    ``None`` is returned when the point:
      * cannot be projected into the raster's CRS (outside the projection domain),
      * falls outside the raster's extent, or
      * lands on a nodata / masked pixel (including NaN in floating-point rasters).
    """
    lon = float(lon)
    lat = float(lat)

    with rasterio.open(raster_path) as src:
        x, y = _to_raster_crs(src, lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        pixel = src.read(1, window=Window(col, row, 1, 1), masked=True)

    if np.ma.getmaskarray(pixel)[0, 0]:
        return None

    value = float(pixel.data[0, 0])
    if math.isnan(value):
        return None
    return value


def _to_raster_crs(src: DatasetReader, lon: float, lat: float) -> tuple[float, float]:
    """Project a WGS84 lon/lat into the dataset's CRS (identity if the CRS is unset)."""
    if src.crs is None:
        return lon, lat

    dst_crs = CRS.from_user_input(src.crs.to_wkt())
    if dst_crs == _WGS84:
        return lon, lat

    transformer = Transformer.from_crs(_WGS84, dst_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return float(x), float(y)