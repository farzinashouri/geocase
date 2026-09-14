import rasterio
from pyproj import Transformer
from rasterio.windows import Window


def sample_at(raster_path, lon, lat):
    """
    Sample a single-band GeoTIFF at a WGS84 location.
    
    Args:
        raster_path: Path to the GeoTIFF file
        lon: Longitude in WGS84
        lat: Latitude in WGS84
    
    Returns:
        The raster value at the location as a float, or None if no data
    """
    with rasterio.open(raster_path) as src:
        # Transform WGS84 coords to raster CRS if needed
        crs = src.crs
        if crs is None:
            x, y = lon, lat
        elif crs.to_string() != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat
        
        # Get pixel indices
        row, col = src.index(x, y)
        row, col = int(row), int(col)
        
        # Check bounds
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        # Read the pixel
        window = Window(col, row, 1, 1)
        data = src.read(1, window=window)
        
        value = data[0, 0]
        
        # Check for nodata
        if src.nodata is not None and value == src.nodata:
            return None
        
        return float(value)