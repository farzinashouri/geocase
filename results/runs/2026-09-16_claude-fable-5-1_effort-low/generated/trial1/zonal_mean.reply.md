```python
"""Zonal mean of a single-band GeoTIFF over a polygon."""

from __future__ import annotations

from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import from_bounds, Window
from shapely.geometry.base import BaseGeometry


def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    """Return the mean of valid pixels whose centres fall inside ``polygon``.

    ``polygon`` must be in the raster's CRS. Pixels equal to the raster's
    nodata value are excluded. Returns ``None`` if no valid pixel centre
    lies inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        transform = src.transform
        nodata = src.nodata

        # Restrict reading to the pixel window covering the polygon's bounds.
        minx, miny, maxx, maxy = polygon.bounds
        try:
            win = from_bounds(minx, miny, maxx, maxy, transform=transform)
        except Exception:
            return None
        full = Window(0, 0, src.width, src.height)
        win = win.round_offsets(op="floor").round_lengths(op="ceil")
        # Expand by one pixel on each side to be safe about edge centres.
        win = Window(win.col_off - 1, win.row_off - 1, win.width + 2, win.height + 2)
        win = win.intersection(full)
        if win.width <= 0 or win.height <= 0:
            return None
        win = Window(int(win.col_off), int(win.row_off), int(win.width), int(win.height))

        data = src.read(1, window=win, masked=False)
        if data.size == 0:
            return None

        # Pixel-centre coordinates for the window.
        rows = np.arange(win.row_off, win.row_off + win.height)
        cols = np.arange(win.col_off, win.col_off + win.width)
        cc, rr = np.meshgrid(cols, rows)
        xs, ys = rasterio.transform.xy(transform, rr.ravel(), cc.ravel(), offset="center")
        xs = np.asarray(xs, dtype=float)
        ys = np.asarray(ys, dtype=float)

    inside = shapely.contains_xy(polygon, xs, ys).reshape(data.shape)

    valid = inside
    if nodata is not None:
        if np.issubdtype(data.dtype, np.floating) and np.isnan(nodata):
            valid = valid & ~np.isnan(data)
        else:
            valid = valid & (data != nodata)
    if np.issubdtype(data.dtype, np.floating):
        valid = valid & np.isfinite(data)

    if not np.any(valid):
        return None

    return float(np.mean(data[valid].astype(np.float64)))
```