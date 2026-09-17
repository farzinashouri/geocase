"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude.

The module has no import-time side effects; all I/O happens inside
:func:`sample_at`.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = CRS.from_epsg(4326)


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the band-1 value of ``raster_path`` at ``(lon, lat)`` in WGS84.

    The point is reprojected from EPSG:4326 into the raster's own CRS before
    lookup, so the GeoTIFF may use any projection. A raster with no CRS is
    assumed to already be in longitude/latitude.

    Returns ``None`` when the point:
      * cannot be projected into the raster's CRS,
      * falls outside the raster extent, or
      * lands on a nodata / masked cell (or a NaN value).
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    with rasterio.open(raster_path) as src:
        if src.count < 1:
            return None

        dst_crs = src.crs if src.crs else _WGS84
        if dst_crs == _WGS84:
            x, y = lon, lat
        else:
            xs, ys = warp_transform(_WGS84, dst_crs, [lon], [lat])
            x, y = float(xs[0]), float(ys[0])
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = Window(col_off=col, row_off=row, width=1, height=1)
        # masked=True honours the nodata value, internal mask bands and alpha.
        cell = src.read(1, window=window, masked=True)

    if cell.size == 0 or np.ma.is_masked(cell):
        return None

    value = float(np.ma.getdata(cell)[0, 0])
    if math.isnan(value):
        return None
    return value