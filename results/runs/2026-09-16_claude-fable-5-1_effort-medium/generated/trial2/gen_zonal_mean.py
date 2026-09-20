"""Zonal mean of a single-band GeoTIFF over a polygon.

The polygon must be expressed in the raster's own CRS. A pixel counts as
"inside" when its centre lies within the polygon (strictly inside or on the
boundary, as defined by shapely's ``contains_xy`` / ``intersects_xy``).
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from rasterio.windows import Window, intersection as window_intersection
from rasterio.errors import WindowError
from shapely import intersects_xy
from shapely.geometry.base import BaseGeometry


def _candidate_window(dataset: rasterio.io.DatasetReader, polygon: BaseGeometry) -> Optional[Window]:
    """Return the integer pixel window covering the polygon's bounds, or None if disjoint."""
    minx, miny, maxx, maxy = polygon.bounds
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        return None

    # Map the four bound corners to fractional pixel coordinates. Using all
    # four corners keeps this correct for rotated/sheared transforms too.
    inv = ~dataset.transform
    corners = [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)]
    cols, rows = zip(*(inv * c for c in corners))

    # Pad by one pixel so floating-point rounding never drops an edge pixel;
    # the centre-in-polygon test below does the precise filtering.
    col_off = math.floor(min(cols)) - 1
    row_off = math.floor(min(rows)) - 1
    col_end = math.ceil(max(cols)) + 1
    row_end = math.ceil(max(rows)) + 1

    candidate = Window(col_off, row_off, col_end - col_off, row_end - row_off)
    full = Window(0, 0, dataset.width, dataset.height)
    try:
        win = window_intersection(candidate, full)
    except WindowError:
        return None
    if win.width <= 0 or win.height <= 0:
        return None
    return win


def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    """Mean of valid pixel values whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF.
    polygon:
        A shapely geometry in the raster's coordinate reference system.

    Returns
    -------
    float or None
        The mean of the selected valid pixels, or ``None`` when no valid pixel
        centre lies inside the polygon. Pixels equal to the raster's nodata
        value are excluded.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as dataset:
        window = _candidate_window(dataset, polygon)
        if window is None:
            return None

        data = dataset.read(1, window=window)
        nodata = dataset.nodata
        transform = dataset.window_transform(window)

    height, width = data.shape
    if height == 0 or width == 0:
        return None

    # Pixel-centre coordinates for every cell in the window.
    rows, cols = np.mgrid[0:height, 0:width]
    col_c = cols.astype(np.float64) + 0.5
    row_c = rows.astype(np.float64) + 0.5
    xs = transform.a * col_c + transform.b * row_c + transform.c
    ys = transform.d * col_c + transform.e * row_c + transform.f

    inside = intersects_xy(polygon, xs, ys)

    if nodata is None:
        valid = np.ones(data.shape, dtype=bool)
    elif isinstance(nodata, float) and math.isnan(nodata):
        valid = ~np.isnan(data)
    else:
        valid = data != nodata

    selected = data[inside & valid]
    if selected.size == 0:
        return None

    return float(np.mean(selected.astype(np.float64)))