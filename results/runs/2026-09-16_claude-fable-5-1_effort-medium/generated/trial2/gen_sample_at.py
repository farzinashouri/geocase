"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude.

The raster may be in any coordinate reference system; the query point is
reprojected into the raster's CRS before sampling. Importing this module has
no side effects.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = CRS.from_epsg(4326)


def _to_raster_crs(dataset, lon: float, lat: float) -> tuple[float, float]:
    """Project a WGS84 lon/lat pair into the dataset's CRS.

    If the dataset has no CRS, the coordinates are assumed to already be in
    the raster's coordinate space.
    """
    if dataset.crs is None:
        return float(lon), float(lat)
    target = CRS.from_user_input(dataset.crs)
    if target.equals(_WGS84):
        return float(lon), float(lat)
    transformer = Transformer.from_crs(_WGS84, target, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return float(x), float(y)


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the value of band 1 at (lon, lat), or None if there is no data.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF (any CRS).
    lon, lat:
        Query location in WGS84 (EPSG:4326) decimal degrees.

    Returns
    -------
    float or None
        The pixel value as a Python float. ``None`` is returned when the point
        falls outside the raster extent, when the pixel is masked/nodata, when
        the value is NaN, or when the projection of the point is undefined.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    with rasterio.open(raster_path) as src:
        x, y = _to_raster_crs(src, lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if row < 0 or col < 0 or row >= src.height or col >= src.width:
            return None

        window = Window(col_off=col, row_off=row, width=1, height=1)
        data = src.read(1, window=window, masked=True)

    if data.size == 0:
        return None
    if np.ma.is_masked(data) and bool(np.ma.getmaskarray(data)[0, 0]):
        return None

    value = data[0, 0]
    if isinstance(value, np.ma.core.MaskedConstant):
        return None

    result = float(value)
    if math.isnan(result):
        return None
    return result