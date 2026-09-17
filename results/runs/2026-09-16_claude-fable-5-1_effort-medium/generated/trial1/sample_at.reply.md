```python
"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import CRS, Transformer

_WGS84 = "EPSG:4326"


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the value of band 1 of ``raster_path`` at (lon, lat) in WGS84.

    Returns ``None`` when the point falls outside the raster extent or hits a
    nodata / masked cell (including NaN). The raster may be in any CRS; the
    point is reprojected into it before sampling. A raster without a CRS is
    assumed to already be in WGS84.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    with rasterio.open(raster_path) as src:
        if src.crs is not None and not CRS.from_user_input(src.crs).equals(CRS.from_user_input(_WGS84)):
            transformer = Transformer.from_crs(_WGS84, src.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if row < 0 or col < 0 or row >= src.height or col >= src.width:
            return None

        data = src.read(1, window=Window(col, row, 1, 1), masked=True)
        if data.size == 0:
            return None

        cell = data[0, 0]
        if np.ma.is_masked(cell):
            return None

        value = float(cell)
        if math.isnan(value):
            return None
        nodata = src.nodata
        if nodata is not None and not (isinstance(nodata, float) and math.isnan(nodata)) and value == float(nodata):
            return None
        return value
```