"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at (lon, lat) in WGS84, or None if no data there.

    The raster may be in any CRS; the point is reprojected into it before
    sampling. None is returned when the point falls outside the raster
    extent, hits a nodata cell, or hits a NaN cell.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"{raster_path!r} has no CRS; cannot locate lon/lat")

        wgs84 = CRS.from_epsg(4326)
        if CRS.from_user_input(src.crs) == wgs84:
            x, y = lon, lat
        else:
            transformer = Transformer.from_crs(wgs84, src.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)

        if not (np.isfinite(x) and np.isfinite(y)):
            return None

        row, col = src.index(x, y)
        if row < 0 or col < 0 or row >= src.height or col >= src.width:
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)
        if data.size == 0 or np.ma.is_masked(data[0, 0]):
            return None

        value = data[0, 0]
        if np.isnan(value):
            return None
        return float(value)