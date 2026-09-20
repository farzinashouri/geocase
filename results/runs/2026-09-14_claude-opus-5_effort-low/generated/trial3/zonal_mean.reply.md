```python
"""Zonal statistics for a single-band raster over a shapely polygon."""

from __future__ import annotations

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window, from_bounds


def zonal_mean(raster_path, polygon):
    """Mean of band-1 pixels whose centres fall inside ``polygon``.

    ``polygon`` must be in the raster's own CRS. Pixels equal to the raster's
    nodata value (and non-finite pixels) are excluded. Returns ``None`` when no
    valid pixel centre lies inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        transform = src.transform
        nodata = src.nodata

        # Restrict the read to the polygon's bounding box, snapped outward by a
        # pixel so no centre near the edge is lost, then clipped to the raster.
        minx, miny, maxx, maxy = polygon.bounds
        window = from_bounds(minx, miny, maxx, maxy, transform=transform)
        col_off = int(np.floor(window.col_off)) - 1
        row_off = int(np.floor(window.row_off)) - 1
        col_end = int(np.ceil(window.col_off + window.width)) + 1
        row_end = int(np.ceil(window.row_off + window.height)) + 1

        col_off = max(col_off, 0)
        row_off = max(row_off, 0)
        col_end = min(col_end, src.width)
        row_end = min(row_end, src.height)
        if col_end <= col_off or row_end <= row_off:
            return None

        window = Window(col_off, row_off, col_end - col_off, row_end - row_off)
        data = src.read(1, window=window)

    rows, cols = np.mgrid[row_off:row_end, col_off:col_end]
    # Pixel centres in raster CRS coordinates.
    xs, ys = transform * (cols + 0.5, rows + 0.5)

    inside = shapely.contains_xy(polygon, np.asarray(xs), np.asarray(ys))
    if not inside.any():
        return None

    values = data[inside]
    if nodata is not None:
        if isinstance(nodata, float) and np.isnan(nodata):
            valid = ~np.isnan(values)
        else:
            valid = values != nodata
        values = values[valid]

    values = values.astype("float64", copy=False)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None

    return float(values.mean())
```