"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at (lon, lat) in WGS84, or None if no data there.

    The raster may be in any CRS; the point is reprojected into it before
    sampling. None is returned when the point falls outside the raster
    extent, hits the nodata value, is masked, or is non-finite.
    """
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        if raster_crs is None:
            raise ValueError(f"{raster_path!r} has no CRS; cannot map lon/lat onto it")

        transformer = Transformer.from_crs(
            CRS.from_epsg(4326), raster_crs, always_xy=True
        )
        x, y = transformer.transform(lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        # Row/col of the pixel containing the point (respects rotated transforms).
        row, col = src.index(x, y)
        if row < 0 or col < 0 or row >= src.height or col >= src.width:
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)
        if data.size == 0 or np.ma.is_masked(data[0, 0]):
            return None

        value = float(data[0, 0])
        if not math.isfinite(value):
            return None
        return value