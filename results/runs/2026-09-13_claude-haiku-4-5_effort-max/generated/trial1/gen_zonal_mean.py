import rasterio
from shapely.geometry import Point
import numpy as np


def zonal_mean(raster_path, polygon):
    """
    Calculate the mean of raster values whose pixel centres fall inside a polygon.
    
    Args:
        raster_path: Path to a single-band GeoTIFF
        polygon: A shapely polygon in the raster's CRS
    
    Returns:
        float: Mean of valid pixel values, or None if no valid pixels fall inside polygon
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        
        height, width = data.shape
        
        # Create mask for pixels inside polygon
        mask = np.zeros((height, width), dtype=bool)
        
        for row in range(height):
            for col in range(width):
                # Calculate pixel centre coordinates
                x = transform.c + (col + 0.5) * transform.a
                y = transform.f + (row + 0.5) * transform.e
                
                # Check if pixel centre is inside polygon
                pixel_centre = Point(x, y)
                if polygon.contains(pixel_centre):
                    mask[row, col] = True
        
        # Get values where mask is True
        values = data[mask]
        
        # Exclude nodata values
        if nodata is not None:
            values = values[values != nodata]
        
        # Return mean or None
        if len(values) == 0:
            return None
        
        return float(np.mean(values))