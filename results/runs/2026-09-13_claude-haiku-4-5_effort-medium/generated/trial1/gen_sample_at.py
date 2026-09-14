import rasterio
from rasterio.transform import rowcol
from rasterio.windows import Window
import pyproj


def sample_at(raster_path, lon, lat):
    """
    Sample a raster value at WGS84 coordinates.
    
    Args:
        raster_path: Path to a single-band GeoTIFF
        lon: Longitude in WGS84
        lat: Latitude in WGS84
    
    Returns:
        The raster value as a float, or None if no data at that location
    """
    with rasterio.open(raster_path) as src:
        # Transform WGS84 coordinates to the raster's CRS if needed
        x, y = lon, lat
        if src.crs:
            transformer = pyproj.Transformer.from_crs('EPSG:4326', src.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        
        # Get the row and column indices from the coordinates
        row, col = rowcol(src.transform, x, y)
        
        # Round to nearest integer pixel
        row, col = int(round(row)), int(round(col))
        
        # Check if the indices are within bounds
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        # Read a single pixel using a window
        window = Window(col, row, 1, 1)
        value = src.read(1, window=window)[0, 0]
        
        # Check for nodata
        if src.nodata is not None and value == src.nodata:
            return None
        
        return float(value)