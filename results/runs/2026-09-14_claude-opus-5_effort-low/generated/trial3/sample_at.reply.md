```python
"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer


def sample_at(raster_path, lon: float, lat: float) -> Optional[float]:
    """Return the band-1 value of ``raster_path`` at WGS84 (``lon``, ``lat``).

    Returns ``None`` when the point falls outside the raster, the raster
    carries no data there (nodata / masked), or the value is NaN.
    """
    with rasterio.open(raster_path) as src:
        dst_crs = src.crs
        if dst_crs is None:
            # No CRS recorded; assume the coordinates are already in raster space.
            x, y = lon, lat
        else:
            transformer = Transformer.from_crs(
                CRS.from_epsg(4326), dst_crs, always_xy=True
            )
            x, y = transformer.transform(lon, lat)

        if not (math.isfinite(x) and math.isfinite(y)):
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
```