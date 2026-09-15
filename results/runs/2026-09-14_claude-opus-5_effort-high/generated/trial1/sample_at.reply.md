```python
"""Point sampling of single-band GeoTIFFs by WGS84 longitude/latitude.

Public API:
    sample_at(raster_path, lon, lat) -> float | None
"""

from __future__ import annotations

import math
from functools import lru_cache
from os import PathLike
from typing import Optional, Union

import numpy as np
import rasterio
from pyproj import CRS as PyprojCRS
from pyproj import Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = "EPSG:4326"


@lru_cache(maxsize=32)
def _transformer(dst_crs_srs: str) -> Transformer:
    """Build (and cache) a lon/lat -> dst_crs transformer.

    Keyed on a string so the cache stays hashable and stable across the
    different CRS classes rasterio may hand back.
    """
    return Transformer.from_crs(_WGS84, PyprojCRS.from_user_input(dst_crs_srs), always_xy=True)


def sample_at(
    raster_path: Union[str, PathLike], lon: float, lat: float
) -> Optional[float]:
    """Return the value of a single-band GeoTIFF at a WGS84 point.

    Args:
        raster_path: Path to a single-band GeoTIFF in any CRS.
        lon: Longitude in WGS84 decimal degrees.
        lat: Latitude in WGS84 decimal degrees.

    Returns:
        The raster value at the point as a ``float``, or ``None`` if the
        raster holds no data there -- the point falls outside the raster
        extent, outside the projection's valid domain, or the covering
        pixel is nodata/masked/NaN.

    Raises:
        ValueError: If the raster is not single-band or has no CRS, so a
            lon/lat cannot be located in it.
        rasterio.errors.RasterioIOError: If the file cannot be opened.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    with rasterio.open(raster_path) as src:
        if src.count != 1:
            raise ValueError(
                f"expected a single-band raster, got {src.count} bands: {raster_path}"
            )
        if src.crs is None:
            raise ValueError(f"raster has no CRS, cannot locate a lon/lat: {raster_path}")

        x, y = _transformer(src.crs.to_wkt()).transform(lon, lat)
        # pyproj returns inf (not an exception) for points outside the
        # projection's domain of validity.
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)  # floor semantics: upper-left-inclusive pixels
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # masked=True folds in the nodata value and any internal/sidecar mask.
        window = Window(col_off=col, row_off=row, width=1, height=1)
        data = src.read(1, window=window, masked=True)

    if data.size == 0 or np.ma.getmaskarray(data).all():
        return None

    value = float(data.item(0))
    if math.isnan(value):
        return None
    return value
```