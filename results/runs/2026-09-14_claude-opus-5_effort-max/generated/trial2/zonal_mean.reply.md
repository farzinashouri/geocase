```python
"""Zonal statistics for a single-band raster.

`zonal_mean` averages the pixels of a GeoTIFF whose centres fall inside a
polygon given in the raster's own CRS. Importing this module has no side
effects.
"""

from __future__ import annotations

import math
import os
from typing import Optional, Union

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window
from shapely.geometry.base import BaseGeometry

__all__ = ["zonal_mean"]


def zonal_mean(
    raster_path: Union[str, os.PathLike],
    polygon: BaseGeometry,
) -> Optional[float]:
    """Mean of the band-1 pixels whose centres lie inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF.
    polygon:
        Shapely geometry expressed in the raster's own coordinate reference
        system. No reprojection is performed.

    Returns
    -------
    float or None
        The mean of the valid pixel values whose centres fall inside the
        polygon, or ``None`` when no such pixel exists. Pixels equal to the
        raster's nodata value are excluded. A centre lying exactly on the
        polygon boundary counts as outside (shapely ``contains`` semantics).
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        window = _bounding_window(src, polygon.bounds)
        if window is None:
            return None
        data = src.read(1, window=window)
        transform = src.window_transform(window)
        nodata = src.nodata

    rows, cols = np.nonzero(_valid_mask(data, nodata))
    if rows.size == 0:
        return None

    # A pixel centre sits half a cell in from the cell's upper-left corner.
    col_c = cols + 0.5
    row_c = rows + 0.5
    xs = transform.a * col_c + transform.b * row_c + transform.c
    ys = transform.d * col_c + transform.e * row_c + transform.f

    shapely.prepare(polygon)
    inside = shapely.contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    return float(data[rows[inside], cols[inside]].mean())


def _bounding_window(src, bounds) -> Optional[Window]:
    """Smallest in-raster window containing every pixel that ``bounds`` can reach.

    Works for rotated and flipped transforms: the four corners of the bounding
    box are mapped into pixel space and the extent of that mapping is used.
    """
    minx, miny, maxx, maxy = bounds
    inverse = ~src.transform
    corners = [inverse * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
    cols = [col for col, _ in corners]
    rows = [row for _, row in corners]

    col_off = max(0, math.floor(min(cols)))
    row_off = max(0, math.floor(min(rows)))
    col_end = min(src.width, math.ceil(max(cols)))
    row_end = min(src.height, math.ceil(max(rows)))
    if col_end <= col_off or row_end <= row_off:
        return None

    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def _valid_mask(data: np.ndarray, nodata) -> np.ndarray:
    """Boolean mask of the pixels that carry a real value."""
    if nodata is None:
        return np.ones(data.shape, dtype=bool)
    if math.isnan(nodata):
        return ~np.isnan(data)
    return data != nodata
```