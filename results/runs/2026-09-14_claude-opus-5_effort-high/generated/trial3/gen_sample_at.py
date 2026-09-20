"""Sample a single-band GeoTIFF at a WGS84 coordinate.

Public API:
    sample_at(raster_path, lon, lat) -> float | None
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Optional, Union
from os import PathLike

import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import CRS, Transformer

__all__ = ["sample_at"]

WGS84 = CRS.from_epsg(4326)


@lru_cache(maxsize=32)
def _transformer(target_srs: str) -> Transformer:
    """Build (and cache) a lon/lat -> target CRS transformer.

    Keyed on the target CRS serialized as WKT so the cache key is hashable.
    """
    return Transformer.from_crs(WGS84, CRS.from_wkt(target_srs), always_xy=True)


def sample_at(
    raster_path: Union[str, PathLike], lon: float, lat: float
) -> Optional[float]:
    """Return the value of a single-band raster at a WGS84 lon/lat.

    Args:
        raster_path: Path to a single-band GeoTIFF, in any CRS.
        lon: Longitude in degrees (WGS84).
        lat: Latitude in degrees (WGS84).

    Returns:
        The pixel value as a float, or None if the raster holds no data
        there -- the point falls outside the raster's extent, the pixel is
        nodata/masked, or the value is NaN.

    Raises:
        rasterio.errors.RasterioIOError: If the file cannot be opened.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    with rasterio.open(raster_path) as src:
        if src.crs is None:
            # Undefined CRS: the only sane reading is that the coordinates
            # are already in the raster's own (assumed geographic) space.
            x, y = lon, lat
        else:
            x, y = _transformer(src.crs.to_wkt()).transform(lon, lat)

        # pyproj returns inf (or nan) for points outside the projection's
        # valid domain rather than raising.
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        row, col = int(row), int(col)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # masked=True honours the nodata value, any internal mask band, and
        # an alpha band, so it covers every way a GeoTIFF says "no data".
        data = src.read(
            1, window=Window(col, row, 1, 1), masked=True, boundless=False
        )

    if data.size == 0 or np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data[0, 0])
    if math.isnan(value):
        return None
    return value