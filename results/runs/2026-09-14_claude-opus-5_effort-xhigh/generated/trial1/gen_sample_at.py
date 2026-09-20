"""Sample a single-band GeoTIFF at a WGS84 coordinate.

The raster may be in any CRS; the input longitude/latitude are reprojected
into the raster's CRS before the pixel lookup.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Optional, Union

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = CRS.from_epsg(4326)


@lru_cache(maxsize=64)
def _transformer(dst_crs_wkt: str) -> Transformer:
    """Build (and cache) a WGS84 -> raster-CRS transformer.

    always_xy=True keeps the argument order (lon, lat) / (easting, northing)
    regardless of the axis order declared by either CRS.
    """
    return Transformer.from_crs(_WGS84, CRS.from_wkt(dst_crs_wkt), always_xy=True)


def sample_at(
    raster_path: Union[str, "os.PathLike[str]"],  # noqa: F821
    lon: float,
    lat: float,
) -> Optional[float]:
    """Return the band-1 value of ``raster_path`` at WGS84 (``lon``, ``lat``).

    Returns ``None`` when the raster holds no data at that location, i.e. the
    point falls outside the raster's extent, the pixel is masked (nodata value,
    internal mask, or alpha band), the pixel value is non-finite, or the
    coordinate cannot be projected into the raster's CRS.

    Raises:
        ValueError: if the raster has no CRS, so (lon, lat) cannot be located.
        rasterio.errors.RasterioIOError: if the file cannot be opened.
    """
    lon = float(lon)
    lat = float(lat)

    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(
                f"{raster_path!r} has no CRS; cannot locate a WGS84 coordinate in it."
            )

        x, y = _transformer(src.crs.to_wkt()).transform(lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            # pyproj yields inf for coordinates outside the target CRS's domain.
            return None

        # index() floors to the containing pixel and honours rotated transforms.
        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # masked=True folds nodata, internal masks and alpha into one mask.
        data = src.read(1, window=Window(col, row, 1, 1), masked=True)

    if data.size == 0 or np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data[0, 0])
    return value if math.isfinite(value) else None