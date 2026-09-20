import rasterio
from rasterio.transform import rowcol
from pyproj import Transformer, CRS


def sample_at(raster_path, lon, lat):
    """
    Sample a raster at a given WGS84 longitude/latitude.
    
    Args:
        raster_path: Path to the GeoTIFF file
        lon: Longitude in WGS84
        lat: Latitude in WGS84
    
    Returns:
        The raster value as a float, or None if no data at that location
    """
    with rasterio.open(raster_path) as src:
        transform = src.transform
        crs = src.crs
        
        # Transform from WGS84 to raster CRS if needed
        x, y = lon, lat
        if crs and crs != CRS.from_epsg(4326):
            transformer = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        
        # Convert geographic coordinates to pixel row/col
        row, col = rowcol(transform, x, y)
        
        # Round to nearest integer pixel
        row, col = int(round(row)), int(round(col))
        
        # Check bounds
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        # Read the value at that pixel
        data = src.read(1, window=((row, row + 1), (col, col + 1)))
        value = data[0, 0]
        
        # Check for nodata
        nodata = src.nodata
        if nodata is not None and value == nodata:
            return None
        
        return float(value)