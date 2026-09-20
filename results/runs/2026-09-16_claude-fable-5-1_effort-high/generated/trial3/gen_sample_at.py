"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window


def _to_raster_coords(dataset: rasterio.DatasetReader, lon: float, lat: float) -> tuple[float, float]:
    """Project a WGS84 lon/lat pair into the dataset's native coordinate system."""
    raster_crs = dataset.crs
    if raster_crs is None:
        # No CRS on the file: treat its coordinates as already being lon/lat.
        return float(lon), float(lat)

    src_crs = CRS.from_epsg(4326)
    dst_crs = CRS.from_user_input(raster_crs.to_wkt())
    if dst_crs == src_crs:
        return float(lon), float(lat)

    # always_xy=True guarantees (lon, lat) -> (x, y) regardless of axis order.
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return float(x), float(y)


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at (lon, lat) as a float, or None if there is no data.

    The point is given in WGS84 (EPSG:4326). The raster may be in any CRS; the
    point is reprojected into the raster's CRS before sampling. None is returned
    when the point falls outside the raster extent, when the projected point is
    not finite, when the pixel holds the nodata value, or when the pixel is NaN.
    """
    with rasterio.open(raster_path) as dataset:
        x, y = _to_raster_coords(dataset, lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            return None

        row, col = dataset.index(x, y)
        if row < 0 or col < 0 or row >= dataset.height or col >= dataset.width:
            return None

        window = Window(col_off=col, row_off=row, width=1, height=1)
        block = dataset.read(1, window=window, masked=True)

        if block.size == 0 or np.ma.is_masked(block) and bool(np.ma.getmaskarray(block)[0, 0]):
            return None

        value = block[0, 0]
        if np.ma.is_masked(value):
            return None

        result = float(value)
        if math.isnan(result):
            return None
        return result