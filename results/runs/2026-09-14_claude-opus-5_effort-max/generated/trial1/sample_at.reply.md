```python
"""Point sampling of single-band GeoTIFFs by WGS84 longitude/latitude.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Optional, Union

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = "EPSG:4326"


@lru_cache(maxsize=64)
def _transformer(dst_crs_wkt: str) -> Transformer:
    """Return a cached lon/lat -> ``dst_crs_wkt`` transformer.

    Keyed on WKT so repeated calls against the same raster reuse one PROJ
    pipeline; ``always_xy`` keeps the argument order (lon, lat) regardless of
    the axis order either CRS declares.
    """
    return Transformer.from_crs(_WGS84, CRS.from_wkt(dst_crs_wkt), always_xy=True)


def sample_at(
    raster_path: Union[str, "os.PathLike[str]"],
    lon: float,
    lat: float,
) -> Optional[float]:
    """Read band 1 of ``raster_path`` at a WGS84 coordinate.

    Args:
        raster_path: Path to a single-band GeoTIFF in any CRS.
        lon: Longitude in degrees east (WGS84).
        lat: Latitude in degrees north (WGS84).

    Returns:
        The pixel value as a ``float``, or ``None`` when the raster holds no
        data there: the point falls outside the grid, the pixel is nodata (or
        masked by an internal/alpha mask), the pixel is NaN, or the coordinate
        has no image in the raster's CRS.

    Raises:
        ValueError: If the dataset is not georeferenced (no CRS), so lon/lat
            cannot be located.
        rasterio.errors.RasterioIOError: If the file cannot be opened.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"{os.fspath(raster_path)!r} has no CRS; cannot locate lon/lat")

        x, y = _transformer(src.crs.to_wkt()).transform(float(lon), float(lat))
        if not (math.isfinite(x) and math.isfinite(y)):
            # PROJ signals "outside the CRS's domain" with infinities.
            return None

        # Inverting the geotransform (rather than comparing against bounds)
        # stays correct for rotated or sheared georeferencing.
        col_f, row_f = ~src.transform * (x, y)
        col, row = math.floor(col_f), math.floor(row_f)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # masked=True applies nodata plus any internal or alpha-band mask.
        data = src.read(1, window=Window(col, row, 1, 1), masked=True)

    if np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data[0, 0])
    if math.isnan(value):
        # Undeclared NaN fill: no nodata value set, but still no data.
        return None
    return value
```