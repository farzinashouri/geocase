"""Zonal statistics helper: area-weighted-free mean of raster pixels under a polygon.

The module exposes a single function, :func:`zonal_mean`, which computes the
arithmetic mean of the band-1 values of a single-band GeoTIFF over the pixels
whose *centres* fall strictly inside a polygon given in the raster's own CRS.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
import os
from typing import Optional, Union

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window

__all__ = ["zonal_mean"]


def _bounds_window(transform, bounds, width: int, height: int) -> Optional[Window]:
    """Smallest pixel window guaranteed to contain every centre inside `bounds`.

    Works for rotated/sheared transforms too: an affine map sends the corners of
    the bounding box to the corners of a parallelogram, so the pixel-space
    bounding box of the four mapped corners covers the whole geometry.
    """
    minx, miny, maxx, maxy = bounds
    inverse = ~transform

    corners = [
        inverse * (minx, miny),
        inverse * (minx, maxy),
        inverse * (maxx, miny),
        inverse * (maxx, maxy),
    ]
    cols = [c for c, _ in corners]
    rows = [r for _, r in corners]

    col_off = max(int(math.floor(min(cols))), 0)
    row_off = max(int(math.floor(min(rows))), 0)
    col_end = min(int(math.ceil(max(cols))), width)
    row_end = min(int(math.ceil(max(rows))), height)

    if col_end <= col_off or row_end <= row_off:
        return None

    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def zonal_mean(
    raster_path: Union[str, "os.PathLike[str]"],
    polygon: "shapely.Geometry",
) -> Optional[float]:
    """Mean of the band-1 pixels whose centres lie inside `polygon`.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF.
    polygon:
        A shapely polygon expressed in the raster's coordinate reference
        system. No reprojection is performed.

    Returns
    -------
    float or None
        The arithmetic mean of the selected valid pixel values, or ``None`` if
        no pixel with a valid value has its centre inside the polygon.

    Notes
    -----
    A centre lying exactly on the polygon boundary is *not* counted (shapely
    ``contains`` semantics). Pixels masked by the dataset (its nodata value or
    an internal/alpha mask) are excluded, as are non-finite values in
    floating-point rasters, which could not otherwise be averaged.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        window = _bounds_window(src.transform, polygon.bounds, src.width, src.height)
        if window is None:
            return None

        # Pixel centres of the window, in raster CRS coordinates.
        cols = window.col_off + 0.5 + np.arange(window.width, dtype="float64")
        rows = window.row_off + 0.5 + np.arange(window.height, dtype="float64")
        col_grid, row_grid = np.meshgrid(cols, rows)

        a, b, c, d, e, f = (src.transform[i] for i in range(6))
        xs = a * col_grid + b * row_grid + c
        ys = d * col_grid + e * row_grid + f

        inside = shapely.contains_xy(polygon, xs, ys)
        if not inside.any():
            return None

        band = src.read(1, window=window, masked=True)

    values = np.ma.getdata(band)
    selected = inside & ~np.ma.getmaskarray(band)
    if values.dtype.kind == "f":
        selected &= np.isfinite(values)

    if not selected.any():
        return None

    return float(values[selected].mean())