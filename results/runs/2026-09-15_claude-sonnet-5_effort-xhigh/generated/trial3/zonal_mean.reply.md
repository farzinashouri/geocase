```python
import numpy as np
import rasterio
import shapely
from rasterio.windows import Window, from_bounds


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        px_minx, px_miny, px_maxx, px_maxy = polygon.bounds
        rs_minx, rs_miny, rs_maxx, rs_maxy = src.bounds

        minx = max(px_minx, rs_minx)
        miny = max(px_miny, rs_miny)
        maxx = min(px_maxx, rs_maxx)
        maxy = min(px_maxy, rs_maxy)

        if minx >= maxx or miny >= maxy:
            return None

        raw_window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)

        col_off = max(int(np.floor(raw_window.col_off)), 0)
        row_off = max(int(np.floor(raw_window.row_off)), 0)
        col_end = min(int(np.ceil(raw_window.col_off + raw_window.width)), src.width)
        row_end = min(int(np.ceil(raw_window.row_off + raw_window.height)), src.height)

        if col_end <= col_off or row_end <= row_off:
            return None

        window = Window(col_off, row_off, col_end - col_off, row_end - row_off)

        data = src.read(1, window=window, masked=True)
        transform = src.window_transform(window)

        rows, cols = data.shape
        row_idx, col_idx = np.mgrid[0:rows, 0:cols]

        xs, ys = transform * (col_idx + 0.5, row_idx + 0.5)
        points = shapely.points(xs.ravel(), ys.ravel())
        inside = shapely.contains(polygon, points).reshape(rows, cols)

        valid_values = data[inside].compressed()

        if valid_values.size == 0:
            return None

        return float(valid_values.mean())
```