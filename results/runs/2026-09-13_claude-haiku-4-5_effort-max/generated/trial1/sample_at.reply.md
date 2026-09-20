```python
import rasterio
from rasterio.transform import rowcol
from pyproj import CRS, Transformer

def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as src:
        if src.crs is not None:
            transformer = Transformer.from_crs(CRS.from_epsg(4326), src.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat
        
        row, col = rowcol(src.transform, x, y)
        row = int(round(row))
        col = int(round(col))
        
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None
        
        data = src.read(1, window=((row, row + 1), (col, col + 1)))
        value = data[0, 0]
        
        if src.nodata is not None and value == src.nodata:
            return None
        
        return float(value)
```