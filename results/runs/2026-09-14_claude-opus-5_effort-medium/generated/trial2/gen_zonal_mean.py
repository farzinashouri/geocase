"""Zonal statistics for a single-band raster.

Provides :func:`zonal_mean`, which averages the pixels of a GeoTIFF whose
centres fall inside a polygon expressed in the raster's own CRS.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely

__all__ = ["zonal_mean"]


def _pixel_centres(transform, row_off: int, col_off: int, height: int, width: int):
    """Return (x, y) arrays of pixel centre coordinates for a raster window.

    Works for rotated/sheared transforms as well as axis-aligned ones.
    """
    rows = np.arange(row_off, row_off + height, dtype="float64") + 0.5
    cols = np.arange(col_off, col_off + width, dtype="float64") + 0.5
    col_grid, row_grid = np.meshgrid(cols, rows)

    a, b, c, d, e, f = (
        transform.a,
        transform.b,
        transform.c,
        transform.d,
        transform.e,
        transform.f,
    )
    xs = c + a * col_grid + b * row_grid
    ys = f + d * col_grid + e * row_grid
    return xs, ys


def _window_for_polygon(src, polygon):
    """Smallest pixel window covering the polygon's bounds, clipped to the raster.

    Returns ``(row_off, col_off, height, width)``; height/width may be 0 when the
    polygon lies outside the raster.
    """
    transform = src.transform
    # A rotated or sheared transform has no axis-aligned pixel window for a
    # bounding box, so fall back to scanning the whole raster.
    if transform.b != 0.0 or transform.d != 0.0:
        return 0, 0, src.height, src.width

    minx, miny, maxx, maxy = polygon.bounds
    inv = ~transform
    xs_ys = [inv * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
    fcols = [p[0] for p in xs_ys]
    frows = [p[1] for p in xs_ys]

    col_start = max(0, int(math.floor(min(fcols))))
    col_stop = min(src.width, int(math.ceil(max(fcols))))
    row_start = max(0, int(math.floor(min(frows))))
    row_stop = min(src.height, int(math.ceil(max(frows))))

    height = max(0, row_stop - row_start)
    width = max(0, col_stop - col_start)
    return row_start, col_start, height, width


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Mean of the band-1 pixels whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path :
        Path to a single-band GeoTIFF.
    polygon :
        A shapely geometry in the same CRS as the raster. A pixel contributes
        when its centre point lies strictly inside the geometry (centres exactly
        on the boundary are not counted).

    Returns
    -------
    float or None
        The mean of the selected valid pixels, or ``None`` when no pixel with a
        valid (non-nodata) value has its centre inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        row_off, col_off, height, width = _window_for_polygon(src, polygon)
        if height == 0 or width == 0:
            return None

        window = rasterio.windows.Window(col_off, row_off, width, height)
        data = src.read(1, window=window)
        nodata = src.nodata
        transform = src.transform

    xs, ys = _pixel_centres(transform, row_off, col_off, height, width)
    inside = shapely.contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    values = data[inside]

    if nodata is not None:
        if isinstance(nodata, float) and math.isnan(nodata):
            valid = ~np.isnan(values.astype("float64", copy=False))
        else:
            valid = values != nodata
        values = values[valid]

    if values.size == 0:
        return None

    return float(np.mean(values.astype("float64", copy=False)))