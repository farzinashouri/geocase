```python
import numpy as np
import rasterio
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    """Calculate the mean of raster values within a polygon."""
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        
        height, width = data.shape
        
        rows, cols = np.mgrid[0:height, 0:width]
        xs = transform.a * (cols + 0.5) + transform.b * (rows + 0.5) + transform.c
        ys = transform.d * (cols + 0.5) + transform.e * (rows + 0.5) + transform.f
        
        mask = np.zeros((height, width), dtype=bool)
        for i in range(height):
            for j in range(width):
                point = Point(xs[i, j], ys[i, j])
                if polygon.contains(point):
                    mask[i, j] = True
        
        valid_mask = mask
        if nodata is not None:
            valid_mask = valid_mask & (data != nodata)
        
        valid_values = data[valid_mask]
        
        if len(valid_values) > 0:
            return float(np.mean(valid_values))
        else:
            return None
```