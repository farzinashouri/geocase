"""Sample a single-band GeoTIFF at a WGS84 coordinate."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer

_WGS84 = CRS.from_epsg(4326)


def sample_at(raster_path, lon: float, lat: float) -> Optional[float]:
    """Return the value of the first band of ``raster_path`` at ``lon``/``lat``.

    ``lon``/``lat`` are WGS84 degrees. Returns ``None`` when the point falls
    outside the raster, when the raster carries a nodata value at that pixel,
    or when the stored value is NaN.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"{raster_path} has no CRS; cannot locate a lon/lat point")

        dst_crs = CRS.from_user_input(src.crs)
        if dst_crs == _WGS84:
            x, y = lon, lat
        else:
            # always_xy keeps the input ordered (lon, lat) regardless of the
            # authority-defined axis order of either CRS.
            transformer = Transformer.from_crs(_WGS84, dst_crs, always_xy=True)
            x, y = transformer.transform(lon, lat)

        if not (math.isfinite(x) and math.isfinite(y)):
            # The point is outside the projection's domain of validity.
            return None

        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)

    if data.size == 0 or np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data[0, 0])
    if math.isnan(value):
        return None
    return value