"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude.

Provides :func:`sample_at`, which reprojects the query point into the
raster's own CRS, reads the pixel under it, and returns the value as a
``float`` -- or ``None`` when the point falls outside the raster or on
nodata.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy.ma as ma
import rasterio
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

_WGS84 = "EPSG:4326"


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at (``lon``, ``lat``) in WGS84, or ``None``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF (any CRS).
    lon, lat:
        Query coordinates as WGS84 longitude and latitude in degrees.

    Returns
    -------
    float or None
        The band-1 pixel value as a ``float``, or ``None`` when the point
        lies outside the raster extent or on a nodata/masked/NaN pixel.

    Raises
    ------
    ValueError
        If the raster has no CRS, so the point cannot be located in it.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(
                f"Raster {raster_path!r} has no CRS; cannot locate a WGS84 point in it."
            )

        # Reproject the WGS84 point into the raster's CRS (x/y order).
        xs, ys = warp_transform(_WGS84, src.crs, [lon], [lat])
        x, y = xs[0], ys[0]
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        # Locate the pixel containing the point.
        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # Read just that pixel, masked so nodata comes back as masked.
        window = Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)
        if data.size == 0:
            return None

        value = data[0, 0]
        if value is ma.masked or ma.is_masked(value):
            return None

        result = float(value)
        if math.isnan(result):
            return None
        return result
