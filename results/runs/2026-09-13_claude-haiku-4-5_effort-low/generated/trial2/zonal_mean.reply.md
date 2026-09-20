```python
import rasterio
import numpy as np
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    """
    Calculate the mean of raster pixel values whose centers fall within a polygon.
    
    Args:
        raster_path: Path to a single-band GeoTIFF
        polygon: Shapely polygon in the raster's coordinate reference system
    
    Returns:
        float: Mean of valid pixel values, or None if no pixels fall within polygon
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        
        valid_values = []
        height, width = data.shape
        
        for row in range(height):
            for col in range(width):
                x, y = transform * (col + 0.5, row + 0.5)
                
                if polygon.contains(Point(x, y)):
                    pixel_value = data[row, col]
                    if nodata is None or pixel_value != nodata:
                        valid_values.append(pixel_value)
        
        if len(valid_values) == 0:
            return None
        return float(np.mean(valid_values))
```