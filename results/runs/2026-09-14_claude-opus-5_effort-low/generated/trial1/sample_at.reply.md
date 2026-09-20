```python
"""Sample a single-band GeoTIFF at a WGS84 coordinate."""

from __future__ import annotations

import math

import numpy as np
import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    """Return the band-1 value of ``raster_path`` at WGS84 ``lon``/``lat``.

    Returns ``None`` if the point falls outside the raster, or if the raster
    carries nodata (or NaN) at that location.
    """
    with rasterio.open(raster_path) as src:
        crs = src.crs
        if crs is None:
            raise ValueError(f"{raster_path} has no CRS; cannot locate a WGS84 point")

        # always_xy keeps the argument order (lon, lat) -> (x, y) regardless of
        # whether the target CRS declares a lat/lon axis order.
        transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        value = src.read(1, window=window, masked=True)[0, 0]

    if value is np.ma.masked:
        return None

    value = float(value)
    return None if math.isnan(value) else value
```