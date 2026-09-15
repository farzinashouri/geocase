"""Point sampling of single-band GeoTIFFs at WGS84 coordinates."""

from __future__ import annotations

import math
from typing import Optional

import rasterio
from pyproj import CRS, Transformer

WGS84 = CRS.from_epsg(4326)


def sample_at(raster_path, lon: float, lat: float) -> Optional[float]:
    """Return the single-band raster value at a WGS84 lon/lat, or None.

    None is returned when the point falls outside the raster, or when the
    pixel there is nodata (including NaN).
    """
    with rasterio.open(raster_path) as src:
        if src.count != 1:
            raise ValueError(f"expected a single-band raster, got {src.count} bands")
        if src.crs is None:
            raise ValueError("raster has no CRS; cannot locate a WGS84 point in it")

        dst_crs = CRS.from_user_input(src.crs)
        if dst_crs.equals(WGS84):
            x, y = float(lon), float(lat)
        else:
            transformer = Transformer.from_crs(WGS84, dst_crs, always_xy=True)
            x, y = transformer.transform(float(lon), float(lat))

        if not (math.isfinite(x) and math.isfinite(y)):
            # pyproj returns inf for points outside the projection's domain.
            return None

        row, col = src.index(x, y, op=math.floor)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)

    if data.size == 0 or data.mask.all():
        return None

    value = float(data.data.flat[0])
    if math.isnan(value):
        return None
    return value