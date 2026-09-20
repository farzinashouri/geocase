```python
import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as dataset:
        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        row, col = dataset.index(x, y)
        if row < 0 or col < 0 or row >= dataset.height or col >= dataset.width:
            return None

        band = dataset.read(1)
        value = band[row, col]

        nodata = dataset.nodata
        if nodata is not None and value == nodata:
            return None

        return float(value)
```