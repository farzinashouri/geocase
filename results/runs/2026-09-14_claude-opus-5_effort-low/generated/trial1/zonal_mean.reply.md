```python
"""Zonal statistics helper: mean of raster pixels whose centres fall in a polygon."""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from shapely import contains_xy


def zonal_mean(raster_path, polygon):
    """Mean of band-1 pixels whose centres lie inside ``polygon``.

    The polygon must be in the raster's own CRS. Pixels equal to the raster's
    nodata value are ignored. Returns ``None`` when no valid pixel centre falls
    inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        minx, miny, maxx, maxy = polygon.bounds

        # Read only the block covering the polygon, clipped to the raster.
        window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        window = window.round_offsets(op="floor").round_lengths(op="ceil")
        # Grow by one pixel so centres on the bounding-box edge are not lost.
        window = Window(
            window.col_off - 1, window.row_off - 1,
            window.width + 2, window.height + 2,
        )
        try:
            window = window.intersection(Window(0, 0, src.width, src.height))
        except rasterio.errors.WindowError:
            return None  # no overlap with the raster
        if window.width <= 0 or window.height <= 0:
            return None

        data = src.read(1, window=window, masked=False)
        nodata = src.nodata
        transform = src.window_transform(window)

    if data.size == 0:
        return None

    # Pixel-centre coordinates for the window.
    rows = np.arange(data.shape[0]) + 0.5
    cols = np.arange(data.shape[1]) + 0.5
    col_grid, row_grid = np.meshgrid(cols, rows)
    xs = transform.a * col_grid + transform.b * row_grid + transform.c
    ys = transform.d * col_grid + transform.e * row_grid + transform.f

    inside = contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    values = data[inside]
    valid = np.isfinite(values) if np.issubdtype(values.dtype, np.floating) else np.ones(values.shape, dtype=bool)
    if nodata is not None:
        if isinstance(nodata, float) and np.isnan(nodata):
            pass  # already excluded by the isfinite check
        else:
            valid &= values != nodata

    values = values[valid]
    if values.size == 0:
        return None

    return float(np.mean(values.astype("float64")))
```