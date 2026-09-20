Write access to a scratch file was declined, so the module below is reviewed by hand but was not executed here.

```python
"""Zonal mean of a single-band GeoTIFF over a polygon.

The polygon must be a shapely geometry expressed in the raster's own CRS.
A pixel contributes to the mean when its centre lies inside the polygon and
its value is not the raster's nodata value (NaN values are treated as nodata).
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window


def _is_nan(value) -> bool:
    try:
        return math.isnan(value)
    except (TypeError, ValueError):
        return False


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Return the mean of pixels whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path : str or path-like
        Path to a single-band GeoTIFF.
    polygon : shapely geometry
        Zone geometry in the raster's coordinate reference system.

    Returns
    -------
    float or None
        Mean of the valid pixel values inside the polygon, or ``None`` if no
        valid pixel centre lies inside it.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        transform = src.transform
        nodata = src.nodata
        height, width = src.height, src.width

        # Limit the read to the pixel-space bounding box of the polygon.
        inv = ~transform
        minx, miny, maxx, maxy = polygon.bounds
        corners = [inv * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
        cols = [c for c, _ in corners]
        rows = [r for _, r in corners]
        col0 = max(int(math.floor(min(cols))), 0)
        col1 = min(int(math.ceil(max(cols))), width)
        row0 = max(int(math.floor(min(rows))), 0)
        row1 = min(int(math.ceil(max(rows))), height)
        if col1 <= col0 or row1 <= row0:
            return None

        window = Window(col0, row0, col1 - col0, row1 - row0)
        data = src.read(1, window=window)

    # World coordinates of every pixel centre in the window.
    col_idx = np.arange(col0, col1, dtype=np.float64) + 0.5
    row_idx = np.arange(row0, row1, dtype=np.float64) + 0.5
    cc, rr = np.meshgrid(col_idx, row_idx)
    xs = transform.a * cc + transform.b * rr + transform.c
    ys = transform.d * cc + transform.e * rr + transform.f

    valid = np.asarray(shapely.contains_xy(polygon, xs, ys), dtype=bool)

    is_float = np.issubdtype(data.dtype, np.floating)
    if is_float:
        valid &= ~np.isnan(data)
    if nodata is not None and not _is_nan(nodata):
        # Compare in the band's own precision so e.g. float32 -3.4e38 matches.
        nd = np.asarray(nodata, dtype=data.dtype) if is_float else nodata
        valid &= data != nd

    if not valid.any():
        return None

    return float(np.mean(data[valid], dtype=np.float64))
```