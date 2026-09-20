"""Zonal mean of a single-band GeoTIFF over a shapely polygon."""

from __future__ import annotations

from typing import Optional

import numpy as np
import rasterio
from rasterio import features
from rasterio.windows import from_bounds
from shapely.geometry import shape as _shape
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Return the mean of valid pixels whose centres fall inside ``polygon``.

    ``polygon`` is a shapely geometry (or GeoJSON-like mapping) in the raster's
    own CRS. Pixels equal to the raster's nodata value are ignored. Returns
    ``None`` when no valid pixel centre lies inside the polygon.
    """
    if not isinstance(polygon, BaseGeometry):
        polygon = _shape(polygon)
    if polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        # Restrict work to the polygon's bounding box, clipped to the raster.
        minx, miny, maxx, maxy = polygon.bounds
        window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        window = window.round_offsets().round_lengths()
        full = rasterio.windows.Window(0, 0, src.width, src.height)
        try:
            window = window.intersection(full)
        except rasterio.errors.WindowError:
            return None
        # Grow by one pixel each side so boundary pixels are not lost to rounding.
        col_off = max(0, int(window.col_off) - 1)
        row_off = max(0, int(window.row_off) - 1)
        col_end = min(src.width, int(window.col_off + window.width) + 1)
        row_end = min(src.height, int(window.row_off + window.height) + 1)
        if col_end <= col_off or row_end <= row_off:
            return None
        window = rasterio.windows.Window(
            col_off, row_off, col_end - col_off, row_end - row_off
        )

        data = src.read(1, window=window, masked=True)
        transform = src.window_transform(window)

    if data.size == 0:
        return None

    # Rasterize the polygon with all_touched=False: a pixel is burned only if
    # its centre is inside the polygon, which is exactly the required test.
    inside = features.rasterize(
        [(polygon, 1)],
        out_shape=data.shape,
        transform=transform,
        fill=0,
        all_touched=False,
        dtype="uint8",
    ).astype(bool)

    valid = inside & ~np.ma.getmaskarray(data)
    if not valid.any():
        return None

    values = np.asarray(data.data, dtype="float64")[valid]
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    return float(values.mean())