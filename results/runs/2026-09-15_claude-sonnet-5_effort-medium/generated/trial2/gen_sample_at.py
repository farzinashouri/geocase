"""Sample a single-band GeoTIFF at a WGS84 lon/lat coordinate."""

from typing import Optional

import rasterio
from pyproj import Transformer


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    with rasterio.open(raster_path) as dataset:
        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        row, col = dataset.index(x, y)
        if row < 0 or row >= dataset.height or col < 0 or col >= dataset.width:
            return None

        band = dataset.read(1, window=((row, row + 1), (col, col + 1)))
        value = band[0, 0]

        nodata = dataset.nodata
        if nodata is not None and value == nodata:
            return None

        return float(value)