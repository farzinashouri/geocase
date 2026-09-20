```python
from typing import Optional

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from shapely import contains_xy
from shapely.geometry.base import BaseGeometry


def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        bounds = src.bounds

        minx, miny, maxx, maxy = polygon.bounds
        minx = max(minx, bounds.left)
        maxx = min(maxx, bounds.right)
        miny = max(miny, bounds.bottom)
        maxy = min(maxy, bounds.top)

        if minx >= maxx or miny >= maxy:
            return None

        window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        window = window.round_lengths(op="ceil").round_offsets(op="floor")
        window = window.intersection(Window(0, 0, src.width, src.height))

        if window.width <= 0 or window.height <= 0:
            return None

        data = src.read(1, window=window)
        win_transform = src.window_transform(window)

        rows, cols = np.indices(data.shape)
        xs, ys = win_transform * (cols + 0.5, rows + 0.5)

        valid = contains_xy(polygon, xs, ys)

        if nodata is not None:
            if isinstance(nodata, float) and np.isnan(nodata):
                valid &= ~np.isnan(data)
            else:
                valid &= data != nodata
        elif np.issubdtype(data.dtype, np.floating):
            valid &= ~np.isnan(data)

        if not np.any(valid):
            return None

        return float(data[valid].mean())
```