```python
import numpy as np
import rasterio
from rasterio.transform import xy
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform

    minx, miny, maxx, maxy = polygon.bounds
    inv_transform = ~transform
    col_min, row_max = inv_transform * (minx, miny)
    col_max, row_min = inv_transform * (maxx, maxy)

    row_start = max(int(np.floor(row_min)), 0)
    row_end = min(int(np.ceil(row_max)), data.shape[0] - 1)
    col_start = max(int(np.floor(col_min)), 0)
    col_end = min(int(np.ceil(col_max)), data.shape[1] - 1)

    values = []
    for row in range(row_start, row_end + 1):
        for col in range(col_start, col_end + 1):
            value = data[row, col]
            if nodata is not None and value == nodata:
                continue
            x, y = xy(transform, row, col)
            if polygon.contains(Point(x, y)):
                values.append(float(value))

    if not values:
        return None

    return float(np.mean(values))
```