import rasterio
import pyproj

def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        
        x, y = lon, lat
        if raster_crs is not None:
            wgs84 = pyproj.CRS("EPSG:4326")
            if not raster_crs.equals(wgs84):
                transformer = pyproj.Transformer.from_crs(
                    wgs84, 
                    raster_crs,
                    always_xy=True
                )
                x, y = transformer.transform(lon, lat)
        
        row, col = src.index(x, y)
        row, col = round(row), round(col)
        
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        data = src.read(1, window=((row, 1), (col, 1)))
        value = data[0, 0]
        
        if src.nodata is not None and value == src.nodata:
            return None
        
        return float(value)