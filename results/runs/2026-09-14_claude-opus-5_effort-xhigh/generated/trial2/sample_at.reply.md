```python
"""Sample a single-band GeoTIFF at a WGS84 coordinate.

The raster may be in any CRS; input coordinates are always interpreted as
WGS84 longitude/latitude (EPSG:4326) and reprojected into the raster's CRS
before lookup.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

_WGS84 = CRS.from_epsg(4326)


@lru_cache(maxsize=32)
def _transformer(dst_wkt: str) -> Transformer:
    """Build (and cache) a WGS84 -> raster-CRS transformer."""
    return Transformer.from_crs(_WGS84, CRS.from_wkt(dst_wkt), always_xy=True)


def _x_candidates(x: float, is_geographic: bool):
    """Longitudes to try, covering rasters wrapped to 0..360 or -360..0."""
    yield x
    if is_geographic:
        yield x + 360.0
        yield x - 360.0


def _read_point(src, x: float, y: float) -> float | None:
    """Read band 1 at map coordinate (x, y); None if outside or nodata."""
    col_f, row_f = ~src.transform * (x, y)
    if not (math.isfinite(col_f) and math.isfinite(row_f)):
        return None

    col, row = math.floor(col_f), math.floor(row_f)
    if not (0 <= row < src.height and 0 <= col < src.width):
        return None

    data = src.read(1, window=Window(col, row, 1, 1), masked=True)
    if data.size == 0 or np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data.data[0, 0])
    if math.isnan(value):
        return None
    return value


def sample_at(raster_path: str | os.PathLike, lon: float, lat: float) -> float | None:
    """Return the band-1 value of `raster_path` at WGS84 (`lon`, `lat`).

    Returns None when the location falls outside the raster, is masked, or
    holds the raster's nodata value (including NaN).

    Raises ValueError if the raster carries no CRS, since the coordinates
    then cannot be located in the raster's space.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"{os.fspath(raster_path)!r} has no CRS; cannot locate WGS84 coordinates")

        x, y = _transformer(src.crs.to_wkt()).transform(float(lon), float(lat))
        if not (math.isfinite(x) and math.isfinite(y)):
            # Outside the projection's domain of validity.
            return None

        for candidate_x in _x_candidates(x, src.crs.is_geographic):
            value = _read_point(src, candidate_x, y)
            if value is not None:
                return value
        return None
```