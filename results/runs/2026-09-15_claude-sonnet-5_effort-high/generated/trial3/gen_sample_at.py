"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

import math

import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as dataset:
        if dataset.crs is not None:
            transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        left, bottom, right, top = dataset.bounds
        if not (left <= x <= right and bottom <= y <= top):
            return None

        value = next(dataset.sample([(x, y)], indexes=1))[0]
        value = float(value)

        if math.isnan(value):
            return None
        if dataset.nodata is not None and value == dataset.nodata:
            return None

        return value