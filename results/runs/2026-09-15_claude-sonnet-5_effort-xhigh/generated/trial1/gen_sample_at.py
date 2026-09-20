import math

import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as dataset:
        if dataset.crs is not None and dataset.crs.to_epsg() != 4326:
            transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        row, col = dataset.index(x, y)
        if row < 0 or row >= dataset.height or col < 0 or col >= dataset.width:
            return None

        window = Window(col, row, 1, 1)
        data = dataset.read(1, window=window, masked=True)
        value = data[0, 0]

        if value is np.ma.masked:
            return None

        value = float(value)
        if math.isnan(value):
            return None

        return value