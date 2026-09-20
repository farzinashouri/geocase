```python
import rasterio
import pyproj


def sample_at(raster_path, lon, lat):
    """
    Sample a raster value at given WGS84 coordinates.
    
    Args:
        raster_path: Path to the GeoTIFF file
        lon: Longitude in WGS84
        lat: Latitude in WGS84
    
    Returns:
        The raster value at the location as a float, or None if no data
    """
    with rasterio.open(raster_path) as src:
        # Get the raster's CRS and determine coordinate transformation
        raster_crs = src.crs
        x, y = lon, lat
        
        # Transform WGS84 coordinates to raster CRS if needed
        if raster_crs is not None:
            wgs84_crs = pyproj.CRS('EPSG:4326')
            if not raster_crs.equals(wgs84_crs):
                transformer = pyproj.Transformer.from_crs(wgs84_crs, raster_crs, always_xy=True)
                x, y = transformer.transform(lon, lat)
        
        # Convert geographic coordinates to pixel indices
        row, col = src.index(x, y)
        
        # Convert to integers (round to nearest pixel)
        col = int(round(col))
        row = int(round(row))
        
        # Check if pixel is within bounds
        if col < 0 or col >= src.width or row < 0 or row >= src.height:
            return None
        
        # Read the value at this pixel
        value = src.read(1, window=((row, row+1), (col, col+1)))
        
        # Check for nodata value
        if src.nodata is not None and value[0, 0] == src.nodata:
            return None
        
        return float(value[0, 0])
```