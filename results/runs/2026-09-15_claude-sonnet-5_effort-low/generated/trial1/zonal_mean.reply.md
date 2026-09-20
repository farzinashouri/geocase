```python
import numpy as np
import rasterio
from rasterio.transform import xy


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        height, width = data.shape

    rows, cols = np.indices((height, width))
    xs, ys = xy(transform, rows.ravel(), cols.ravel())
    xs = np.array(xs)
    ys = np.array(ys)

    from shapely.vectorized import contains
    mask = contains(polygon, xs, ys).reshape(height, width)

    values = data[mask]

    if nodata is not None:
        values = values[values != nodata]

    if values.size == 0:
        return None

    return float(np.mean(values))
```