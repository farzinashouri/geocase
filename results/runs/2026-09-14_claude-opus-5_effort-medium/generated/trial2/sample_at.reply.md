```python
"""Point sampling from a single-band GeoTIFF.

Exposes :func:`sample_at`, which returns the raster value at a WGS84
longitude/latitude, reprojecting the point into the raster's own CRS first.
"""

from __future__ import annotations

import math
from typing import Optional

import rasterio
from pyproj import CRS, Transformer

__all__ = ["sample_at"]

_WGS84 = CRS.from_epsg(4326)


def sample_at(raster_path, lon: float, lat: float) -> Optional[float]:
    """Return the value of a single-band raster at a WGS84 coordinate.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF, in any CRS.
    lon, lat:
        Longitude and latitude in WGS84 decimal degrees.

    Returns
    -------
    The sampled value as a ``float``, or ``None`` if the point falls outside
    the raster, or the raster stores nodata/NaN there.
    """
    with rasterio.open(raster_path) as src:
        x, y = _to_raster_crs(src.crs, float(lon), float(lat))
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y, op=math.floor)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)

    if data.size == 0 or data.mask.all():
        return None

    value = float(data.item(0))
    if not math.isfinite(value):
        return None
    return value


def _to_raster_crs(raster_crs, lon: float, lat: float):
    """Project a WGS84 lon/lat into the raster's CRS (x, y) coordinates."""
    if raster_crs is None:
        # Undefined CRS: the only sensible reading is that the transform is
        # already in lon/lat degrees.
        return lon, lat

    target = CRS.from_user_input(raster_crs)
    if target.equals(_WGS84):
        return lon, lat

    transformer = Transformer.from_crs(_WGS84, target, always_xy=True)
    return transformer.transform(lon, lat)
```