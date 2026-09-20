"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

import math
import os

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = "EPSG:4326"


def sample_at(raster_path: str | os.PathLike[str], lon: float, lat: float) -> float | None:
    """Return the value of band 1 of ``raster_path`` at (``lon``, ``lat``).

    ``lon`` and ``lat`` are WGS84 degrees. They are reprojected into the
    raster's own coordinate reference system before the containing pixel is
    looked up, so the raster may use any CRS (including rotated transforms).

    Returns ``None`` when the point falls outside the raster's extent, when
    the pixel is masked (declared nodata value, internal mask, or alpha band),
    when the stored value is NaN, or when the point cannot be projected into
    the raster's CRS (e.g. outside the projection's valid domain).

    Raises ``ValueError`` if the raster carries no CRS, because the
    longitude/latitude could not be located without one.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"{os.fspath(raster_path)!r} has no CRS; cannot locate lon/lat")

        # always_xy=True guarantees (x, y) == (lon, lat) ordering regardless of
        # the axis order the CRS definitions declare (EPSG:4326 is lat/lon).
        transformer = Transformer.from_crs(_WGS84, src.crs.to_wkt(), always_xy=True)
        x, y = transformer.transform(lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            # pyproj reports points outside the projection's domain as inf.
            return None

        # index() applies the inverse affine, so rotated/sheared rasters work too.
        row, col = src.index(x, y)
        row, col = int(row), int(col)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        pixel = src.read(1, window=Window(col, row, 1, 1), masked=True)

    if np.ma.getmaskarray(pixel)[0, 0]:
        return None

    value = float(pixel.data[0, 0])
    if math.isnan(value):
        return None
    return value