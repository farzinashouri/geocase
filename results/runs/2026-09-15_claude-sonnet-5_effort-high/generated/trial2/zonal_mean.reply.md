```python
import numpy as np
import rasterio
from shapely.vectorized import contains


def zonal_mean(raster_path, polygon):
    """Mean of valid pixel values whose centres fall inside `polygon`."""
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata

    rows, cols = data.shape
    col_idx, row_idx = np.meshgrid(
        np.arange(cols, dtype=np.float64),
        np.arange(rows, dtype=np.float64),
    )

    a, b, c, d, e, f = (
        transform.a,
        transform.b,
        transform.c,
        transform.d,
        transform.e,
        transform.f,
    )
    col_centres = col_idx + 0.5
    row_centres = row_idx + 0.5
    xs = a * col_centres + b * row_centres + c
    ys = d * col_centres + e * row_centres + f

    inside = contains(polygon, xs, ys)

    if nodata is not None:
        valid = data != nodata
        if np.isnan(nodata):
            valid = ~np.isnan(data)
        inside &= valid
    else:
        inside &= ~np.isnan(data) if np.issubdtype(data.dtype, np.floating) else inside

    if not np.any(inside):
        return None

    return float(data[inside].mean())
```