```python
"""Zonal mean of a single-band GeoTIFF over a shapely polygon.

The polygon must be expressed in the raster's own coordinate reference
system. A pixel contributes to the mean when its centre lies inside the
polygon and its value is not the raster's nodata value.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import rasterio
from rasterio import features
from shapely.geometry import shape as _shape
from shapely.geometry.base import BaseGeometry


def _as_geometry(polygon) -> BaseGeometry:
    """Accept a shapely geometry or a GeoJSON-like mapping."""
    if isinstance(polygon, BaseGeometry):
        return polygon
    return _shape(polygon)


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Return the mean of valid pixel values whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF readable by rasterio.
    polygon:
        A shapely geometry (or GeoJSON-like mapping) in the raster's CRS.

    Returns
    -------
    float or None
        The mean of the selected pixels, or ``None`` if no pixel with a
        valid (non-nodata) value has its centre inside the polygon.
    """
    geom = _as_geometry(polygon)
    if geom.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        # Restrict work to the window covering the polygon's bounding box.
        # Clamp to the raster extent; an empty overlap means no pixels.
        minx, miny, maxx, maxy = geom.bounds
        window = rasterio.windows.from_bounds(
            minx, miny, maxx, maxy, transform=src.transform
        )
        # Pad by one pixel so pixels on the edge are not lost to rounding,
        # then clamp to the dataset.
        row_off = int(np.floor(window.row_off)) - 1
        col_off = int(np.floor(window.col_off)) - 1
        row_end = int(np.ceil(window.row_off + window.height)) + 1
        col_end = int(np.ceil(window.col_off + window.width)) + 1
        row_off = max(row_off, 0)
        col_off = max(col_off, 0)
        row_end = min(row_end, src.height)
        col_end = min(col_end, src.width)
        if row_end <= row_off or col_end <= col_off:
            return None

        window = rasterio.windows.Window(
            col_off, row_off, col_end - col_off, row_end - row_off
        )
        transform = src.window_transform(window)
        data = src.read(1, window=window)
        nodata = src.nodata

    # Rasterise the polygon using pixel-centre containment. With
    # all_touched=False rasterio burns a pixel only when its centre lies
    # inside the geometry, which is exactly the required rule.
    inside = features.rasterize(
        [(geom, 1)],
        out_shape=data.shape,
        transform=transform,
        fill=0,
        all_touched=False,
        dtype="uint8",
    ).astype(bool)

    valid = inside
    if nodata is not None:
        if np.isnan(nodata):
            valid = valid & ~np.isnan(data)
        else:
            valid = valid & (data != nodata)
    # Always drop NaNs for floating rasters, since they carry no value.
    if np.issubdtype(data.dtype, np.floating):
        valid = valid & ~np.isnan(data)

    if not valid.any():
        return None

    return float(data[valid].astype(np.float64).mean())
```