"""Zonal statistics for a single-band raster and a shapely polygon.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Mean of band-1 pixels whose centres fall inside ``polygon``.

    ``polygon`` must already be expressed in the raster's CRS.  Pixels equal to
    the raster's nodata value (and NaN pixels) are ignored.  Returns ``None`` if
    no valid pixel centre lies inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        window = _covering_window(src, polygon)
        if window is None:
            return None
        values = src.read(1, window=window)
        transform = src.window_transform(window)
        nodata = src.nodata

    if values.size == 0:
        return None

    rows, cols = np.mgrid[0:values.shape[0], 0:values.shape[1]]
    xs, ys = _cell_centres(transform, rows, cols)

    inside = shapely.contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    selected = values[inside].astype("float64")
    valid = ~np.isnan(selected)
    if nodata is not None and not math.isnan(float(nodata)):
        valid &= selected != float(nodata)
    if not valid.any():
        return None

    return float(selected[valid].mean())


def _cell_centres(transform, rows, cols):
    """Map integer (row, col) indices to pixel-centre map coordinates."""
    col_c = cols + 0.5
    row_c = rows + 0.5
    xs = transform.c + transform.a * col_c + transform.b * row_c
    ys = transform.f + transform.d * col_c + transform.e * row_c
    return xs, ys


def _covering_window(src, polygon):
    """Smallest read window guaranteed to contain every candidate pixel."""
    transform = src.transform

    # Rotated / sheared grids: fall back to the full raster rather than guess.
    if transform.b != 0.0 or transform.d != 0.0:
        if src.width == 0 or src.height == 0:
            return None
        return Window(0, 0, src.width, src.height)

    minx, miny, maxx, maxy = polygon.bounds
    inverse = ~transform
    corners = [
        inverse * (x, y)
        for x, y in ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy))
    ]
    cs = [c for c, _ in corners]
    rs = [r for _, r in corners]

    # One pixel of slack absorbs any float fuzz at the window edges.
    col_off = max(0, int(math.floor(min(cs))) - 1)
    row_off = max(0, int(math.floor(min(rs))) - 1)
    col_end = min(src.width, int(math.ceil(max(cs))) + 1)
    row_end = min(src.height, int(math.ceil(max(rs))) + 1)

    if col_end <= col_off or row_end <= row_off:
        return None

    return Window(col_off, row_off, col_end - col_off, row_end - row_off)