```python
"""Zonal mean of a single-band GeoTIFF over a polygon."""

from __future__ import annotations

from typing import Optional

import numpy as np
import rasterio
from rasterio import features
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry


def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    """Return the mean of valid pixels whose centres fall inside ``polygon``.

    ``polygon`` must be in the raster's CRS. Pixels equal to the raster's
    nodata value are ignored. Returns ``None`` when no valid pixel centre
    lies inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        nodata = src.nodata

        # Restrict work to the window covering the polygon's bounding box,
        # clipped to the raster extent.
        minx, miny, maxx, maxy = polygon.bounds
        win = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        row_off = int(np.floor(win.row_off))
        col_off = int(np.floor(win.col_off))
        row_end = int(np.ceil(win.row_off + win.height))
        col_end = int(np.ceil(win.col_off + win.width))
        row_off = max(row_off, 0)
        col_off = max(col_off, 0)
        row_end = min(row_end, src.height)
        col_end = min(col_end, src.width)
        if row_end <= row_off or col_end <= col_off:
            return None
        window = Window(col_off, row_off, col_end - col_off, row_end - row_off)

        data = src.read(1, window=window, masked=False)
        transform = src.window_transform(window)

        # Rasterize with all_touched=False so only pixels whose centres are
        # inside the polygon are selected.
        inside = features.rasterize(
            [(mapping(polygon), 1)],
            out_shape=data.shape,
            transform=transform,
            fill=0,
            all_touched=False,
            dtype="uint8",
        ).astype(bool)

    if nodata is not None:
        if np.isnan(nodata):
            valid = ~np.isnan(data)
        else:
            valid = data != nodata
        inside &= valid
    if np.issubdtype(data.dtype, np.floating):
        inside &= ~np.isnan(data)

    if not inside.any():
        return None
    return float(np.mean(data[inside].astype(np.float64)))
```