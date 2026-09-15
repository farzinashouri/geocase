"""Point sampling of a single-band GeoTIFF at WGS84 coordinates.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Optional, Union

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]


@lru_cache(maxsize=32)
def _transformer_to(dst_crs_wkt: str) -> Transformer:
    """Cached WGS84 -> raster-CRS transformer (keyed by WKT, so it is hashable)."""
    return Transformer.from_crs(
        CRS.from_epsg(4326), CRS.from_wkt(dst_crs_wkt), always_xy=True
    )


def sample_at(
    raster_path: str, lon: float, lat: float
) -> Optional[float]:
    """Return the value of a single-band raster at a WGS84 lon/lat.

    The raster may be in any CRS; the coordinate is reprojected into the
    raster's CRS before lookup. Returns ``None`` when the raster has no data
    at that location -- i.e. the point falls outside the raster's extent, the
    pixel holds the nodata value or is masked out, or the pixel is NaN.

    Args:
        raster_path: Path to a single-band GeoTIFF.
        lon: Longitude in degrees (EPSG:4326).
        lat: Latitude in degrees (EPSG:4326).

    Returns:
        The pixel value as a ``float``, or ``None`` if there is no data there.
    """
    lon = float(lon)
    lat = float(lat)

    with rasterio.open(raster_path) as dataset:
        if dataset.crs is None:
            # Undefined CRS: the only sane reading is that the raster is
            # already in lon/lat degrees.
            x, y = lon, lat
        else:
            x, y = _transformer_to(dataset.crs.to_wkt()).transform(lon, lat)

        # pyproj returns inf/nan for coordinates outside the projection's
        # domain of validity rather than raising.
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        # Inverse of the geotransform, floored to pixel indices. Handles
        # rotated/sheared transforms too.
        row, col = dataset.index(x, y)
        row, col = int(row), int(col)
        if not (0 <= row < dataset.height and 0 <= col < dataset.width):
            return None

        # masked=True folds the nodata value, per-dataset masks and alpha
        # bands into a single mask.
        window = Window(col_off=col, row_off=row, width=1, height=1)
        data = dataset.read(1, window=window, masked=True)

    if data.size == 0 or np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data.data[0, 0])
    if math.isnan(value):
        return None
    return value