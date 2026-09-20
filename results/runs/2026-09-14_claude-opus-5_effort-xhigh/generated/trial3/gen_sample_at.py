"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude.

The raster may be stored in any CRS; the query point is reprojected from
EPSG:4326 into the raster's CRS before the pixel lookup.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = "EPSG:4326"


@lru_cache(maxsize=32)
def _transformer(target_wkt: str) -> Transformer:
    """Return a cached lon/lat -> target-CRS transformer.

    Keyed by WKT so repeated calls against the same raster (or against rasters
    sharing a CRS) reuse one transformer; building one is comparatively costly.
    """
    return Transformer.from_crs(_WGS84, CRS.from_wkt(target_wkt), always_xy=True)


def sample_at(
    raster_path: "str | os.PathLike[str]", lon: float, lat: float
) -> Optional[float]:
    """Return band 1's value at ``(lon, lat)``, or ``None`` if there is no data.

    Args:
        raster_path: Path to a single-band GeoTIFF.
        lon: Longitude in WGS84 degrees.
        lat: Latitude in WGS84 degrees.

    Returns:
        The pixel value as a ``float``, or ``None`` when the point falls
        outside the raster's extent or the projection's valid domain, or when
        the covering pixel is nodata/masked or NaN.

    A raster with no CRS is assumed to be indexed by the supplied coordinates
    directly, since no reprojection is possible.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            x, y = float(lon), float(lat)
        else:
            x, y = _transformer(src.crs.to_wkt()).transform(lon, lat)

        # pyproj yields infinities for points outside the projection's domain.
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # masked=True honours the nodata value, an internal mask, or an alpha band.
        value = src.read(1, window=Window(col, row, 1, 1), masked=True)[0, 0]

    if value is np.ma.masked:
        return None

    value = float(value)
    return value if math.isfinite(value) else None