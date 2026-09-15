```python
"""Sample a single-band GeoTIFF at a WGS84 coordinate."""

from __future__ import annotations

import math
from typing import Optional

import rasterio
from pyproj import CRS, Transformer


def sample_at(raster_path, lon: float, lat: float) -> Optional[float]:
    """Return the band-1 value of ``raster_path`` at WGS84 ``lon``/``lat``.

    Returns ``None`` when the point falls outside the raster or the pixel
    there holds nodata (including NaN).
    """
    wgs84 = CRS.from_epsg(4326)

    with rasterio.open(raster_path) as src:
        dst_crs = src.crs
        if dst_crs is None:
            # No CRS recorded; assume the coordinates are already native.
            x, y = float(lon), float(lat)
        elif CRS.from_user_input(dst_crs).equals(wgs84):
            x, y = float(lon), float(lat)
        else:
            transformer = Transformer.from_crs(
                wgs84, CRS.from_user_input(dst_crs), always_xy=True
            )
            x, y = transformer.transform(float(lon), float(lat))

        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y, op=math.floor)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)

    if data.mask.all():
        return None

    value = float(data.filled(float("nan"))[0, 0])
    if math.isnan(value):
        return None
    return value
```