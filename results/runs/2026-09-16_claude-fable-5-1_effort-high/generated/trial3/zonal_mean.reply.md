Writing the module now: it reads only the window covering the polygon's bounds, computes pixel-centre coordinates from the affine transform, tests them with shapely's vectorised `contains_xy`, and averages the unmasked (non-nodata) values.

```python
"""Zonal mean of a single-band GeoTIFF over a polygon.

The polygon must be expressed in the raster's own coordinate reference
system. A pixel contributes to the mean when its centre lies strictly
inside the polygon and its value is not the raster's nodata value.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window
from shapely.geometry.base import BaseGeometry


def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    """Return the mean of valid pixels whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF (band 1 is used).
    polygon:
        A shapely geometry in the raster's CRS.

    Returns
    -------
    float or None
        Mean of the selected pixel values, or ``None`` if no valid pixel
        has its centre inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        width, height = src.width, src.height
        transform = src.transform
        inverse = ~transform

        # Pixel-space bounding box of the polygon (handles rotated grids by
        # projecting all four corners of the polygon's envelope), padded by
        # one pixel on each side and clipped to the raster extent.
        minx, miny, maxx, maxy = polygon.bounds
        corners = ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy))
        pix = [inverse * corner for corner in corners]
        cols = [c for c, _ in pix]
        rows = [r for _, r in pix]

        col_off = max(int(math.floor(min(cols))) - 1, 0)
        row_off = max(int(math.floor(min(rows))) - 1, 0)
        col_end = min(int(math.ceil(max(cols))) + 1, width)
        row_end = min(int(math.ceil(max(rows))) + 1, height)

        if col_end <= col_off or row_end <= row_off:
            return None

        window = Window(col_off, row_off, col_end - col_off, row_end - row_off)
        # masked=True marks nodata pixels (including NaN nodata) as masked.
        data = src.read(1, window=window, masked=True)

    # Pixel-centre coordinates for the window: centre of pixel (r, c) is at
    # pixel-space (c + 0.5, r + 0.5).
    col_centres = np.arange(col_off, col_end, dtype=float) + 0.5
    row_centres = np.arange(row_off, row_end, dtype=float) + 0.5
    cc, rr = np.meshgrid(col_centres, row_centres)
    a, b, c, d, e, f = transform.a, transform.b, transform.c, transform.d, transform.e, transform.f
    xs = a * cc + b * rr + c
    ys = d * cc + e * rr + f

    inside = shapely.contains_xy(polygon, xs, ys)
    valid = ~np.ma.getmaskarray(data)
    values = np.asarray(data.data)
    if np.issubdtype(values.dtype, np.floating):
        valid &= ~np.isnan(values)

    selected = values[inside & valid]
    if selected.size == 0:
        return None

    return float(np.mean(selected.astype(np.float64)))
```