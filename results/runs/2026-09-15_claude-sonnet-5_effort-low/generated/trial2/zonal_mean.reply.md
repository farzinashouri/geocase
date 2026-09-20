```python
import numpy as np
import rasterio
from rasterio.transform import xy


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform

    rows, cols = np.indices(data.shape)
    xs, ys = xy(transform, rows.ravel(), cols.ravel())
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    from shapely import points, contains

    pts = points(xs, ys)
    inside = contains(polygon, pts).reshape(data.shape)

    values = data[inside]

    if nodata is not None:
        values = values[values != nodata]

    if values.size == 0:
        return None

    return float(np.mean(values))
```