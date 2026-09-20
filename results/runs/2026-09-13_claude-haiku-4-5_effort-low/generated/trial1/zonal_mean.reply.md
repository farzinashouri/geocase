```python
import numpy as np
import rasterio
from shapely.geometry import Point
from shapely.prepared import prep


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        raster_data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        height, width = raster_data.shape
        
        prepared_polygon = prep(polygon)
        valid_values = []
        
        for row in range(height):
            for col in range(width):
                x, y = transform * (col + 0.5, row + 0.5)
                
                if prepared_polygon.contains(Point(x, y)):
                    value = raster_data[row, col]
                    if nodata is None or value != nodata:
                        valid_values.append(float(value))
        
        return float(np.mean(valid_values)) if valid_values else None
```