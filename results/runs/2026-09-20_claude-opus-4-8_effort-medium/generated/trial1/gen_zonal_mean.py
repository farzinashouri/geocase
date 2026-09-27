"""Zonal statistics for a single-band raster over a shapely polygon."""

from __future__ import annotations

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window


def zonal_mean(raster_path, polygon):
    """Mean of pixel values whose centres fall inside ``polygon``.

    Opens the single-band GeoTIFF at ``raster_path`` and returns, as a
    ``float``, the mean of every pixel whose centre lies inside ``polygon``
    (a shapely geometry expressed in the raster's own CRS). Pixels equal to
    the raster's nodata value are excluded. Returns ``None`` when no valid
    pixel has its centre inside the polygon.
    """
    with rasterio.open(raster_path) as src:
        transform = src.transform
        nodata = src.nodata
        width, height = src.width, src.height

        # Restrict work to the pixel window covering the polygon's bounds.
        minx, miny, maxx, maxy = polygon.bounds
        rows, cols = rasterio.transform.rowcol(
            transform,
            [minx, minx, maxx, maxx],
            [miny, maxy, miny, maxy],
            op=float,
        )
        row_min = int(np.floor(min(rows)))
        row_max = int(np.ceil(max(rows)))
        col_min = int(np.floor(min(cols)))
        col_max = int(np.ceil(max(cols)))

        # Clip to the raster extent.
        row_min = max(row_min, 0)
        col_min = max(col_min, 0)
        row_max = min(row_max, height)
        col_max = min(col_max, width)

        if row_min >= row_max or col_min >= col_max:
            return None

        window = Window(col_min, row_min, col_max - col_min, row_max - row_min)
        data = src.read(1, window=window)

    n_rows, n_cols = data.shape
    if n_rows == 0 or n_cols == 0:
        return None

    # Pixel-centre coordinates for the window (offset by half a pixel).
    row_idx = np.arange(row_min, row_max) + 0.5
    col_idx = np.arange(col_min, col_max) + 0.5
    col_grid, row_grid = np.meshgrid(col_idx, row_idx)
    xs, ys = rasterio.transform.xy(transform, row_grid.ravel(), col_grid.ravel())
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    inside = shapely.contains_xy(polygon, xs, ys).reshape(data.shape)

    valid = inside
    if nodata is not None:
        if np.isnan(nodata):
            valid = valid & ~np.isnan(data)
        else:
            valid = valid & (data != nodata)
    # Guard against NaN pixels even when no nodata is declared.
    valid = valid & ~(np.isnan(data) if np.issubdtype(data.dtype, np.floating) else np.zeros_like(data, dtype=bool))

    selected = data[valid]
    if selected.size == 0:
        return None

    return float(np.mean(selected.astype(np.float64)))