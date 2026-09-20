"""Sample a single-band GeoTIFF at a WGS84 coordinate.

Importing this module has no side effects beyond importing its dependencies.
"""

from __future__ import annotations

import math
import os

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

__all__ = ["sample_at"]

WGS84 = "EPSG:4326"


def sample_at(
    raster_path: str | os.PathLike[str], lon: float, lat: float
) -> float | None:
    """Return the value of ``raster_path``'s first band at ``lon``/``lat``.

    ``lon`` and ``lat`` are WGS84 degrees (x first, y second). The raster may be
    in any CRS; the point is reprojected into it before lookup. No interpolation
    is done: the value returned is that of the cell whose extent contains the
    point.

    Returns ``None`` when the raster holds no data there, which covers a point
    outside the raster's extent, a point on a nodata/masked cell, and a NaN
    cell value.

    Raises:
        ValueError: if the raster is not georeferenced (no CRS).
        rasterio.errors.RasterioIOError: if the raster cannot be opened.
    """
    with rasterio.open(raster_path) as dataset:
        if dataset.crs is None:
            raise ValueError(f"{os.fspath(raster_path)!r} has no CRS to locate the point in")

        # always_xy keeps both sides in (x, y) order, so lon/lat is not silently
        # swapped for CRSs whose authority definition is latitude-first.
        transformer = Transformer.from_crs(WGS84, dataset.crs.to_wkt(), always_xy=True)
        x, y = transformer.transform(lon, lat)

        # pyproj returns infinities rather than raising for points outside the
        # target projection's domain (e.g. the far side of the globe from a
        # UTM zone), which is simply "no data here".
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = dataset.index(x, y)
        if not (0 <= row < dataset.height and 0 <= col < dataset.width):
            return None

        window = Window(col_off=col, row_off=row, width=1, height=1)
        data = dataset.read(1, window=window, masked=True)

    # getmaskarray normalises the nomask case (raster with no nodata value).
    if np.ma.getmaskarray(data)[0, 0]:
        return None

    value = float(data[0, 0])
    return None if math.isnan(value) else value