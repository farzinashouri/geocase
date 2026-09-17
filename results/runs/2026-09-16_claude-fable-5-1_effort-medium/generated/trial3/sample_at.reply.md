```python
"""Sample a single-band GeoTIFF at a WGS84 longitude/latitude."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

_WGS84 = CRS.from_epsg(4326)


def _to_raster_coords(dataset, lon: float, lat: float) -> Optional[tuple]:
    """Project (lon, lat) into the dataset's CRS. Returns None if unprojectable."""
    if dataset.crs is None:
        # No CRS on the raster: assume its coordinates are already lon/lat.
        return float(lon), float(lat)

    raster_crs = CRS.from_user_input(dataset.crs)
    if raster_crs.equals(_WGS84):
        x, y = float(lon), float(lat)
    else:
        transformer = Transformer.from_crs(_WGS84, raster_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return x, y


def sample_at(raster_path: str, lon: float, lat: float) -> Optional[float]:
    """Return the raster value at (lon, lat) in WGS84, or None if no data there.

    The raster may be in any CRS; the point is reprojected before sampling.
    None is returned when the point falls outside the raster extent, when the
    pixel is masked/nodata, or when the value is NaN.
    """
    with rasterio.open(raster_path) as dataset:
        coords = _to_raster_coords(dataset, lon, lat)
        if coords is None:
            return None
        x, y = coords

        try:
            row, col = dataset.index(x, y)
        except (ValueError, OverflowError):
            return None

        if not (0 <= row < dataset.height and 0 <= col < dataset.width):
            return None

        data = dataset.read(
            1,
            window=Window(col_off=col, row_off=row, width=1, height=1),
            masked=True,
        )

    if data.size == 0:
        return None
    if np.ma.is_masked(data) and bool(np.ma.getmaskarray(data)[0, 0]):
        return None

    value = float(np.asarray(data)[0, 0])
    if math.isnan(value):
        return None
    return value
```