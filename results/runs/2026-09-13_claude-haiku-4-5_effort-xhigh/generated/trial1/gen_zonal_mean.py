import numpy as np
import rasterio
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    """
    Calculate the mean of raster values whose pixel centres fall inside a polygon.
    
    Args:
        raster_path: Path to a single-band GeoTIFF
        polygon: A shapely polygon in the raster's CRS
        
    Returns:
        float: Mean of valid pixel values inside the polygon
        None: If no valid pixels fall inside the polygon
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        
        valid_values = []
        
        for row in range(data.shape[0]):
            for col in range(data.shape[1]):
                value = data[row, col]
                
                if nodata is not None and value == nodata:
                    continue
                
                x = transform.c + (col + 0.5) * transform.a
                y = transform.f + (row + 0.5) * transform.e
                
                if polygon.contains(Point(x, y)):
                    valid_values.append(float(value))
        
        if not valid_values:
            return None
        return float(np.mean(valid_values))