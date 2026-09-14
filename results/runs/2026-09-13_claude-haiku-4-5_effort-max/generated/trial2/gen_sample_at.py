import rasterio
import rasterio.crs
import rasterio.transform
import rasterio.windows
import pyproj


def sample_at(raster_path, lon, lat):
    """
    Sample a raster at a given WGS84 longitude/latitude.
    
    Args:
        raster_path: Path to a single-band GeoTIFF
        lon: Longitude in WGS84 (EPSG:4326)
        lat: Latitude in WGS84 (EPSG:4326)
    
    Returns:
        float: The raster value at the given location, or None if no data
    """
    with rasterio.open(raster_path) as src:
        src_crs = src.crs
        transform = src.transform
        
        # Transform coordinates from WGS84 to the raster's CRS if needed
        if src_crs is None:
            x, y = lon, lat
        else:
            wgs84_crs = rasterio.crs.CRS.from_epsg(4326)
            if src_crs != wgs84_crs:
                transformer = pyproj.Transformer.from_crs(
                    wgs84_crs,
                    src_crs,
                    always_xy=True
                )
                x, y = transformer.transform(lon, lat)
            else:
                x, y = lon, lat
        
        # Convert geographic coordinates to row/col indices
        row, col = rasterio.transform.rowcol(transform, x, y)
        
        # Convert to integers for indexing
        row, col = int(row), int(col)
        
        # Check bounds
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        # Read a 1x1 window
        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window)
        value = data[0, 0]
        
        # Check for nodata
        nodata = src.nodata
        if nodata is not None and value == nodata:
            return None
        
        return float(value)