"""Zonal statistics for a single-band raster and a shapely polygon.

The polygon must already be expressed in the raster's coordinate reference
system; no reprojection is performed.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from shapely import contains_xy


def zonal_mean(raster_path, polygon):
    """Mean of the band-1 pixels whose centres fall inside ``polygon``.

    Pixels holding the raster's nodata value (and NaNs in floating point
    bands) are ignored. Returns ``None`` when no valid pixel centre lies
    inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        minx, miny, maxx, maxy = polygon.bounds

        # Restrict the read to the polygon's bounding box, snapped outward to
        # whole pixels and clipped to the raster extent.
        try:
            window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        except Exception:
            # Non-invertible or rotated transforms: fall back to the full grid.
            window = Window(0, 0, src.width, src.height)
        window = window.round_offsets(op="floor").round_lengths(op="ceil")
        # One pixel of slack so centres on the bbox edge are not dropped.
        window = Window(
            window.col_off - 1, window.row_off - 1,
            window.width + 2, window.height + 2,
        )
        window = window.intersection(Window(0, 0, src.width, src.height))
        if window.width <= 0 or window.height <= 0:
            return None

        data = src.read(1, window=window, masked=True)
        transform = src.window_transform(window)

    if data.size == 0:
        return None

    rows, cols = np.mgrid[0:data.shape[0], 0:data.shape[1]]
    # Pixel centres, via the full affine so rotated/sheared grids work too.
    c = cols + 0.5
    r = rows + 0.5
    xs = transform.a * c + transform.b * r + transform.c
    ys = transform.d * c + transform.e * r + transform.f

    inside = contains_xy(polygon, xs, ys)

    valid = np.ma.getmaskarray(data) == False  # noqa: E712 - element-wise
    values = np.ma.getdata(data)
    if np.issubdtype(values.dtype, np.floating):
        valid &= np.isfinite(values)

    selected = values[inside & valid]
    if selected.size == 0:
        return None

    return float(selected.mean(dtype=np.float64))