import numpy as np
import rasterio
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    """
    Calculate the mean of raster pixel values whose centers fall within a polygon.
    
    Args:
        raster_path: Path to a single-band GeoTIFF
        polygon: A shapely polygon in the raster's CRS
        
    Returns:
        float: Mean of pixel values inside polygon, or None if no valid pixels found
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        height, width = data.shape
        
        valid_values = []
        
        for row in range(height):
            for col in range(width):
                x, y = transform * (col + 0.5, row + 0.5)
                if polygon.contains(Point(x, y)):
                    value = data[row, col]
                    if nodata is None or value != nodata:
                        valid_values.append(value)
        
        if not valid_values:
            return None
        
        return float(np.mean(valid_values))