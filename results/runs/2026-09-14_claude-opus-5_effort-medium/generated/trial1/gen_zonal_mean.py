"""Zonal statistics for a single-band raster.

Provides :func:`zonal_mean`, which averages the pixels of a single-band
GeoTIFF whose centres fall inside a polygon given in the raster's own CRS.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window, from_bounds, intersection, transform as window_transform

__all__ = ["zonal_mean"]


def _read_window(src) -> Window:
    """Full extent of ``src`` as a window."""
    return Window(0, 0, src.width, src.height)


def _polygon_window(src, bounds) -> Optional[Window]:
    """Smallest pixel-aligned window covering ``bounds``, clipped to the raster.

    Returns ``None`` when the polygon does not overlap the raster at all.
    A rotated/sheared transform is not axis-aligned, so the bounds trick does
    not apply and the full raster window is used instead.
    """
    t = src.transform
    if t.b != 0 or t.d != 0:
        return _read_window(src)

    minx, miny, maxx, maxy = bounds
    win = from_bounds(minx, miny, maxx, maxy, transform=t)

    # Pad by one pixel on every side so that centres on the very edge of the
    # bounding box cannot be lost to floating-point rounding.
    col_off = math.floor(win.col_off) - 1
    row_off = math.floor(win.row_off) - 1
    width = math.ceil(win.col_off + win.width) + 1 - col_off
    height = math.ceil(win.row_off + win.height) + 1 - row_off
    padded = Window(col_off, row_off, max(width, 0), max(height, 0))

    try:
        clipped = intersection(padded, _read_window(src))
    except rasterio.errors.WindowError:
        return None
    if clipped.width <= 0 or clipped.height <= 0:
        return None
    return clipped


def _pixel_centres(t, window: Window):
    """Arrays of x and y coordinates of the centre of every pixel in ``window``."""
    wt = window_transform(window, t)
    cols, rows = np.meshgrid(
        np.arange(window.width, dtype="float64") + 0.5,
        np.arange(window.height, dtype="float64") + 0.5,
    )
    xs = wt.a * cols + wt.b * rows + wt.c
    ys = wt.d * cols + wt.e * rows + wt.f
    return xs, ys


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Mean of the pixels of ``raster_path`` whose centres lie inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF.
    polygon:
        A shapely geometry expressed in the raster's own CRS.

    Returns
    -------
    float or None
        The mean of the selected valid pixels, or ``None`` if no pixel with a
        valid (non-nodata, non-NaN) value has its centre inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        window = _polygon_window(src, polygon.bounds)
        if window is None:
            return None

        data = src.read(1, window=window)
        if data.size == 0:
            return None

        xs, ys = _pixel_centres(src.transform, window)

        # Strict containment: a centre exactly on the boundary is excluded.
        inside = shapely.contains_xy(polygon, xs, ys)
        if not inside.any():
            return None

        values = data[inside]

        valid = np.ones(values.shape, dtype=bool)
        nodata = src.nodata
        if nodata is not None:
            if isinstance(nodata, float) and math.isnan(nodata):
                valid &= ~np.isnan(values)
            else:
                valid &= values != nodata
        if np.issubdtype(values.dtype, np.floating):
            valid &= np.isfinite(values)

        values = values[valid]
        if values.size == 0:
            return None

        return float(np.mean(values.astype("float64")))