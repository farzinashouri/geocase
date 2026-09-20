"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude.

The raster may be in any coordinate reference system; the query point is
reprojected from EPSG:4326 into the raster's CRS before lookup.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the value of band 1 of ``raster_path`` at (``lon``, ``lat``).

    Coordinates are WGS84 (EPSG:4326) longitude/latitude in degrees. The
    result is a ``float``, or ``None`` when the location falls outside the
    raster's extent, cannot be projected into the raster's CRS, or hits a
    nodata / masked cell.
    """
    with rasterio.open(raster_path) as ds:
        # Reproject the query point into the raster's CRS. A raster with no
        # CRS is assumed to already be in geographic lon/lat.
        if ds.crs is None:
            x, y = float(lon), float(lat)
        else:
            transformer = Transformer.from_crs(
                CRS.from_epsg(4326), ds.crs, always_xy=True
            )
            x, y = transformer.transform(lon, lat)

        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        # Map projected coordinates to a pixel row/col and bounds-check it.
        row, col = ds.index(x, y)
        if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
            return None

        # Read exactly one pixel, letting rasterio apply nodata, internal
        # masks and alpha bands.
        data = ds.read(
            1, window=Window(col, row, 1, 1), masked=True
        )

    if np.ma.is_masked(data):
        return None

    value = float(np.asarray(data)[0, 0])
    if math.isnan(value):
        return None
    return value