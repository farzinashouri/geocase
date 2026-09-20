```python
"""Point sampling of a single-band GeoTIFF at WGS84 coordinates.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]


@lru_cache(maxsize=32)
def _transformer_to(dst_wkt: str) -> Transformer:
    """Build (and reuse) a WGS84 -> dst_wkt transformer.

    Constructing a Transformer is far more expensive than using one, and
    callers typically sample the same raster many times.
    """
    return Transformer.from_crs("EPSG:4326", dst_wkt, always_xy=True)


def sample_at(
    raster_path: str | os.PathLike, lon: float, lat: float
) -> float | None:
    """Return the value of band 1 at a WGS84 point, or None if there is none.

    The raster may be in any CRS; ``lon``/``lat`` are always interpreted as
    WGS84 degrees and reprojected into the raster's CRS before sampling.
    Sampling is nearest-neighbour: the value of the pixel containing the
    point is returned as-is, with no interpolation.

    None is returned when the point falls outside the raster's extent, when
    the point cannot be projected into the raster's CRS, or when the pixel
    there is nodata, masked, or NaN.

    Raises:
        ValueError: the raster is not georeferenced (it has no CRS).
        rasterio.errors.RasterioIOError: the raster could not be opened.
    """
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(
                f"{os.fspath(raster_path)!r} has no CRS; "
                "cannot locate a WGS84 point in it"
            )

        x, y = _transformer_to(src.crs.to_wkt()).transform(float(lon), float(lat))
        # pyproj reports unprojectable points as inf rather than raising.
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = src.index(x, y)
        row, col = int(row), int(col)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # masked=True honours the band's nodata value as well as any alpha
        # band or internal/sidecar mask.
        window = Window(col_off=col, row_off=row, width=1, height=1)
        value = src.read(1, window=window, masked=True)[0, 0]

    if np.ma.is_masked(value):
        return None

    value = float(value)
    # Float rasters often carry NaN as an undeclared nodata marker.
    return None if math.isnan(value) else value
```