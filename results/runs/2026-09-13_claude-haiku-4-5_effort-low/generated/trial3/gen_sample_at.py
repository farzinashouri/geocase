import rasterio
from rasterio.transform import rowcol
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    """
    Sample a raster at a given WGS84 longitude/latitude.
    
    Args:
        raster_path: Path to the GeoTIFF file
        lon: WGS84 longitude
        lat: WGS84 latitude
    
    Returns:
        float: The raster value at the location, or None if no data
    """
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        
        # Transform coordinates to raster CRS if needed
        if raster_crs and str(raster_crs) != 'EPSG:4326':
            transformer = Transformer.from_crs('EPSG:4326', raster_crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat
        
        # Get pixel row and column
        row, col = rowcol(src.transform, x, y)
        row, col = int(row), int(col)
        
        # Check if coordinates are within bounds
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        # Read the pixel value
        value = src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
        
        # Return None if nodata value
        if src.nodata is not None and value == src.nodata:
            return None
        
        return float(value)