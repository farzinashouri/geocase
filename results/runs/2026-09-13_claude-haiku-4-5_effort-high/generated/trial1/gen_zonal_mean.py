import rasterio
import numpy as np
from shapely.geometry import Point
from shapely.prepared import prep

def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        
        height, width = data.shape
        prepared = prep(polygon)
        
        valid_values = []
        
        for row in range(height):
            for col in range(width):
                x = transform.c + (col + 0.5) * transform.a
                y = transform.f + (row + 0.5) * transform.e
                
                if prepared.contains(Point(x, y)):
                    value = data[row, col]
                    if nodata is None or value != nodata:
                        valid_values.append(float(value))
        
        return float(np.mean(valid_values)) if valid_values else None