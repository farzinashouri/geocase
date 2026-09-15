```python
import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as ds:
        transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        row, col = ds.index(x, y)
        if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
            return None

        band = ds.read(1, window=((row, row + 1), (col, col + 1)))
        value = band[0, 0]

        nodata = ds.nodata
        if nodata is not None and value == nodata:
            return None

        return float(value)
```