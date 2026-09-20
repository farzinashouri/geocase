```python
"""Zonal mean of a single-band raster over a polygon.

A pixel contributes to the mean when the point at the centre of its cell falls
inside the polygon (points exactly on the boundary are excluded, matching
``shapely``'s ``contains``) and its value is not the raster's nodata value.
The polygon is assumed to already be expressed in the raster's own CRS.

Only the window covering the polygon's bounding box is read, but that window is
read in one go, so memory use scales with the polygon's bounding box.
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
    raster_path: Union[str, os.PathLike], polygon: BaseGeometry
) -> Optional[float]:
    """Return the mean of band 1 over the pixels whose centres lie in ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF.
    polygon:
        Shapely geometry in the raster's CRS.

    Returns
    -------
    The mean as a ``float``, or ``None`` when no pixel with a valid value has
    its centre inside the polygon.
    """
    if polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        window = _covering_window(src.transform, src.width, src.height, polygon.bounds)
        if window is None:
            return None

        band = src.read(1, window=window, masked=True)
        values = np.ma.getdata(band)
        valid = ~np.ma.getmaskarray(band)
        _drop_nodata(valid, values, src.nodata)
        if not valid.any():
            return None

        rows, cols = np.nonzero(valid)
        xs, ys = _cell_centres(
            src.transform, rows + int(window.row_off), cols + int(window.col_off)
        )

    # Preparing builds an index over the polygon's edges; it is a pure speed-up
    # for the many point-in-polygon tests and leaves the geometry unchanged.
    shapely.prepare(polygon)
    inside = shapely.contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    # float64 accumulation so float32 rasters do not lose precision.
    return float(np.mean(values[valid][inside], dtype=np.float64))


def _drop_nodata(valid: np.ndarray, values: np.ndarray, nodata) -> None:
    """Clear ``valid`` wherever ``values`` holds the nodata value, in place."""
    if nodata is None:
        return
    if math.isnan(nodata):
        valid &= ~np.isnan(values)
    else:
        valid &= values != nodata


def _cell_centres(transform, rows: np.ndarray, cols: np.ndarray):
    """Map integer pixel indices to the map coordinates of the cell centres."""
    x = cols + 0.5
    y = rows + 0.5
    return (
        transform.a * x + transform.b * y + transform.c,
        transform.d * x + transform.e * y + transform.f,
    )


def _covering_window(transform, width: int, height: int, bounds) -> Optional[Window]:
    """On-raster window covering ``bounds``, or ``None`` if the two are disjoint."""
    minx, miny, maxx, maxy = bounds
    inverse = ~transform
    corners = [
        inverse * (x, y)
        for x, y in ((minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy))
    ]
    cols = [col for col, _ in corners]
    rows = [row for _, row in corners]

    # Transforming all four corners keeps this correct for rotated and flipped
    # transforms. A pixel of slack on each side absorbs floating-point error;
    # the window only has to be a superset, since the containment test above is
    # what actually decides membership.
    col_start = max(0, math.floor(min(cols)) - 1)
    col_stop = min(width, math.ceil(max(cols)) + 1)
    row_start = max(0, math.floor(min(rows)) - 1)
    row_stop = min(height, math.ceil(max(rows)) + 1)
    if col_stop <= col_start or row_stop <= row_start:
        return None

    return Window(
        col_off=col_start,
        row_off=row_start,
        width=col_stop - col_start,
        height=row_stop - row_start,
    )
```