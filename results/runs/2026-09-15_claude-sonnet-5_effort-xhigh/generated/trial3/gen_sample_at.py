"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude location."""

from typing import Optional

import rasterio
from pyproj import Transformer


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    with rasterio.open(raster_path) as dataset:
        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        row, col = dataset.index(x, y)
        if row < 0 or col < 0 or row >= dataset.height or col >= dataset.width:
            return None

        window = ((row, row + 1), (col, col + 1))
        value = dataset.read(1, window=window)[0, 0]

        if dataset.nodata is not None and value == dataset.nodata:
            return None

        mask = dataset.read_masks(1, window=window)
        if mask[0, 0] == 0:
            return None

        return float(value)