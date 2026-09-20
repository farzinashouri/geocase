"""Zonal statistics for a single-band GeoTIFF.

`zonal_mean` averages the pixels whose centres fall strictly inside a polygon
expressed in the raster's own CRS, ignoring nodata pixels.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window


def _pixel_window(dataset, bounds) -> Optional[Window]:
    """Smallest window covering `bounds`, padded by a pixel and clipped to the grid.

    Corners are mapped through the inverse transform so rotated/sheared
    geotransforms are handled as well as plain north-up ones.
    """
    minx, miny, maxx, maxy = bounds
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        return None

    inverse = ~dataset.transform
    corners = [inverse * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
    cols = [col for col, _ in corners]
    rows = [row for _, row in corners]

    col_off = max(int(math.floor(min(cols))) - 1, 0)
    row_off = max(int(math.floor(min(rows))) - 1, 0)
    col_end = min(int(math.ceil(max(cols))) + 1, dataset.width)
    row_end = min(int(math.ceil(max(rows))) + 1, dataset.height)
    if col_end <= col_off or row_end <= row_off:
        return None
    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def _valid_mask(data: np.ndarray, nodata) -> np.ndarray:
    """Boolean mask of pixels that carry a real measurement."""
    if np.issubdtype(data.dtype, np.floating):
        # NaN is never a usable value, whatever the declared nodata is.
        mask = np.isfinite(data)
        if nodata is not None and math.isfinite(nodata):
            mask &= data != nodata
        return mask
    if nodata is None:
        return np.ones(data.shape, dtype=bool)
    return data != nodata


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Mean of the band-1 pixels whose centres lie inside `polygon`.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF (anything ``rasterio.open`` accepts).
    polygon:
        Shapely geometry in the raster's CRS.

    Returns
    -------
    The mean as a ``float``, or ``None`` when no valid pixel centre is inside.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as dataset:
        window = _pixel_window(dataset, polygon.bounds)
        if window is None:
            return None
        data = dataset.read(1, window=window)
        nodata = dataset.nodatavals[0]
        transform = dataset.window_transform(window)

    valid = _valid_mask(data, nodata)
    if not valid.any():
        return None

    # Only the valid pixels are worth a point-in-polygon test.
    rows, cols = np.nonzero(valid)
    centre_cols = cols + 0.5
    centre_rows = rows + 0.5
    xs = transform.a * centre_cols + transform.b * centre_rows + transform.c
    ys = transform.d * centre_cols + transform.e * centre_rows + transform.f

    inside = shapely.contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    values = data[rows[inside], cols[inside]].astype("float64", copy=False)
    return float(values.mean())