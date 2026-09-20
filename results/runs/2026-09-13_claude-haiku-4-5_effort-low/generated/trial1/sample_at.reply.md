```python
import rasterio
from pyproj import Transformer, CRS


def sample_at(raster_path, lon, lat):
    """
    Sample a value from a single-band GeoTIFF at the given WGS84 coordinates.
    
    Args:
        raster_path: Path to the GeoTIFF file
        lon: Longitude in WGS84
        lat: Latitude in WGS84
    
    Returns:
        The raster value as a float, or None if no data at that location
    """
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        wgs84_crs = CRS.from_epsg(4326)
        
        # Transform coordinates from WGS84 to raster CRS if needed
        if raster_crs is not None and raster_crs != wgs84_crs:
            transformer = Transformer.from_crs(wgs84_crs, raster_crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat
        
        # Convert geographic coordinates to pixel indices
        row, col = src.index(x, y)
        row, col = int(round(row)), int(round(col))
        
        # Check bounds
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None
        
        # Read the pixel value
        value = src.read(1, window=((row, row + 1), (col, col + 1)))
        pixel_value = value[0, 0]
        
        # Check for nodata
        if src.nodata is not None and pixel_value == src.nodata:
            return None
        
        return float(pixel_value)
```