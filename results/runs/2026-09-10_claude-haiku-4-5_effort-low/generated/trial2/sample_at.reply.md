```python
import rasterio
from rasterio.transform import rowcol
from rasterio.crs import CRS
from rasterio.windows import Window
import pyproj


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as src:
        wgs84 = CRS.from_epsg(4326)
        
        if src.crs != wgs84:
            transformer = pyproj.Transformer.from_crs(
                "EPSG:4326",
                src.crs,
                always_xy=True
            )
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat
        
        row, col = rowcol(src.transform, x, y)
        row, col = int(row), int(col)
        
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        window = Window(col, row, 1, 1)
        value = src.read(1, window=window)
        
        if src.nodata is not None and value[0, 0] == src.nodata:
            return None
        
        return float(value[0, 0])
```