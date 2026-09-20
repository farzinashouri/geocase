"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at (lon, lat) in WGS84, or None if no data.

    The point is reprojected from EPSG:4326 into the raster's CRS before
    sampling. Returns None when the point falls outside the raster bounds,
    hits the raster's nodata value, is masked, or is not finite.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"{raster_path!r} has no CRS; cannot locate lon/lat")

        xs, ys = warp_transform("EPSG:4326", src.crs, [lon], [lat])
        x, y = xs[0], ys[0]
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if row < 0 or col < 0 or row >= src.height or col >= src.width:
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        arr = src.read(1, window=window, masked=True)
        if arr.size == 0 or np.ma.is_masked(arr[0, 0]):
            return None

        value = float(arr[0, 0])
        if not math.isfinite(value):
            return None
        return value