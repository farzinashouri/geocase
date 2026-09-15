```python
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as dataset:
        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        row, col = dataset.index(x, y)
        if not (0 <= row < dataset.height and 0 <= col < dataset.width):
            return None

        data = dataset.read(1, window=Window(col, row, 1, 1), masked=True)
        value = data[0, 0]

        if value is np.ma.masked:
            return None

        return float(value)
```