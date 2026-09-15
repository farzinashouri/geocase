```python
"""Zonal mean of single-band raster pixel values whose centres fall inside a polygon."""

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window, from_bounds


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        transform = src.transform

        left, bottom, right, top = src.bounds
        pminx, pminy, pmaxx, pmaxy = polygon.bounds

        minx, maxx = max(left, pminx), min(right, pmaxx)
        miny, maxy = max(bottom, pminy), min(top, pmaxy)

        if minx >= maxx or miny >= maxy:
            return None

        window = from_bounds(minx, miny, maxx, maxy, transform=transform)
        window = window.round_offsets(op="floor").round_lengths(op="ceil")
        window = window.intersection(Window(0, 0, src.width, src.height))

        if window.width <= 0 or window.height <= 0:
            return None

        data = src.read(1, window=window)
        if data.size == 0:
            return None

        win_transform = src.window_transform(window)

        rows, cols = np.indices(data.shape)
        xs, ys = win_transform * (cols + 0.5, rows + 0.5)

        points = shapely.points(xs, ys)
        inside = shapely.contains(polygon, points)

        if nodata is None:
            valid = inside
        elif np.isnan(nodata):
            valid = inside & ~np.isnan(data)
        else:
            valid = inside & (data != nodata)

        if not np.any(valid):
            return None

        return float(data[valid].mean())
```