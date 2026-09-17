"""Zonal mean of a single-band GeoTIFF over a polygon."""

from __future__ import annotations

import math

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window


def zonal_mean(raster_path, polygon):
    """Mean of valid pixel values whose centres fall inside ``polygon``.

    The polygon must be in the raster's coordinate reference system. Pixels
    equal to the raster's nodata value are ignored. Returns ``None`` when no
    valid pixel centre lies inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        transform = src.transform
        height, width = src.height, src.width

        # Restrict work to the pixel window covering the polygon's bounds.
        minx, miny, maxx, maxy = polygon.bounds
        inv = ~transform
        corners = [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)]
        cols_rows = [inv * (x, y) for x, y in corners]
        col_min = max(0, int(math.floor(min(c for c, _ in cols_rows))))
        col_max = min(width, int(math.ceil(max(c for c, _ in cols_rows))))
        row_min = max(0, int(math.floor(min(r for _, r in cols_rows))))
        row_max = min(height, int(math.ceil(max(r for _, r in cols_rows))))
        if col_max <= col_min or row_max <= row_min:
            return None

        window = Window(col_min, row_min, col_max - col_min, row_max - row_min)
        data = src.read(1, window=window, masked=True)

    if data.size == 0:
        return None

    # Pixel-centre coordinates for every cell in the window.
    rows = np.arange(row_min, row_max, dtype=np.float64) + 0.5
    cols = np.arange(col_min, col_max, dtype=np.float64) + 0.5
    cc, rr = np.meshgrid(cols, rows)
    xs = transform.a * cc + transform.b * rr + transform.c
    ys = transform.d * cc + transform.e * rr + transform.f

    inside = shapely.contains_xy(polygon, xs, ys)
    valid = inside & ~np.ma.getmaskarray(data)

    values = np.asarray(data.data)[valid].astype(np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    return float(values.mean())