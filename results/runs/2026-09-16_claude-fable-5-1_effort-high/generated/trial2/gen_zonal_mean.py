"""Zonal mean of a single-band GeoTIFF over a polygon.

The mean is taken over every pixel whose centre lies inside the polygon.
Pixels equal to the raster's nodata value are ignored.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window
from shapely.geometry.base import BaseGeometry


def _candidate_window(dataset: rasterio.DatasetReader, polygon: BaseGeometry) -> Optional[Window]:
    """Return the pixel window that could contain the polygon, or None if disjoint.

    For rotated or sheared transforms the whole raster is returned, since a
    bounds-based window is not well defined in that case.
    """
    height, width = dataset.height, dataset.width
    full = Window(0, 0, width, height)
    t = dataset.transform

    if t.b != 0.0 or t.d != 0.0:
        return full

    minx, miny, maxx, maxy = polygon.bounds
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        return None

    inv = ~t
    corners = [inv * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
    cols = [c for c, _ in corners]
    rows = [r for _, r in corners]

    # Expand by one pixel each way so pixel centres near the edge are kept,
    # then clip to the raster extent.
    col_off = max(0, int(math.floor(min(cols))) - 1)
    row_off = max(0, int(math.floor(min(rows))) - 1)
    col_end = min(width, int(math.ceil(max(cols))) + 1)
    row_end = min(height, int(math.ceil(max(rows))) + 1)

    if col_end <= col_off or row_end <= row_off:
        return None
    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def zonal_mean(raster_path, polygon: BaseGeometry) -> Optional[float]:
    """Mean of valid pixel values whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path
        Path to a single-band GeoTIFF (anything rasterio can open).
    polygon
        A shapely geometry in the raster's coordinate reference system.

    Returns
    -------
    float or None
        The mean of the selected pixels, or ``None`` when no pixel with a
        valid (non-nodata) value has its centre inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as dataset:
        window = _candidate_window(dataset, polygon)
        if window is None:
            return None

        # masked=True marks nodata pixels (including NaN nodata) as masked.
        data = dataset.read(1, window=window, masked=True)
        if data.size == 0:
            return None

        # Pixel-centre coordinates for every cell in the window.
        rows = np.arange(window.row_off, window.row_off + window.height) + 0.5
        cols = np.arange(window.col_off, window.col_off + window.width) + 0.5
        col_grid, row_grid = np.meshgrid(cols, rows)
        t = dataset.transform
        xs = t.a * col_grid + t.b * row_grid + t.c
        ys = t.d * col_grid + t.e * row_grid + t.f

    geom = polygon
    shapely.prepare(geom)
    inside = shapely.contains_xy(geom, xs, ys)

    valid = inside & ~np.ma.getmaskarray(data)
    if not valid.any():
        return None

    values = np.asarray(np.ma.getdata(data), dtype=np.float64)[valid]
    finite = np.isfinite(values)
    if not finite.any():
        return None

    return float(values[finite].mean())