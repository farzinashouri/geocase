```python
"""Zonal mean of a single-band GeoTIFF over a polygon.

The mean is taken over every pixel whose *centre* lies strictly inside the
polygon (boundary points do not count), excluding pixels equal to the raster's
nodata value.  The polygon must be expressed in the raster's own CRS.
"""

from __future__ import annotations

import math
from os import PathLike
from typing import Optional, Union

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window
from shapely.geometry.base import BaseGeometry


def _covering_window(src: rasterio.DatasetReader, polygon: BaseGeometry) -> Optional[Window]:
    """Smallest integer pixel window that covers the polygon's bounding box.

    Works for any affine transform (including rotated/sheared ones) by mapping
    the four corners of the bounding box into pixel space.  Returns ``None``
    if the window does not intersect the raster at all.
    """
    inv = ~src.transform
    minx, miny, maxx, maxy = polygon.bounds
    corners = [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)]
    cols, rows = zip(*(inv * corner for corner in corners))

    col0 = max(0, math.floor(min(cols)))
    row0 = max(0, math.floor(min(rows)))
    col1 = min(src.width, math.ceil(max(cols)))
    row1 = min(src.height, math.ceil(max(rows)))

    if col1 <= col0 or row1 <= row0:
        return None
    return Window(col0, row0, col1 - col0, row1 - row0)


def zonal_mean(
    raster_path: Union[str, PathLike],
    polygon: BaseGeometry,
) -> Optional[float]:
    """Mean of band-1 pixels whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path
        Path to a single-band GeoTIFF (any rasterio-readable raster works).
    polygon
        A shapely geometry in the raster's coordinate reference system.

    Returns
    -------
    float or None
        The mean of the selected valid pixels, or ``None`` when no valid
        pixel has its centre inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        window = _covering_window(src, polygon)
        if window is None:
            return None
        data = src.read(1, window=window)
        nodata = src.nodata
        transform = src.window_transform(window)

    if data.size == 0:
        return None

    # Pixel-centre coordinates for every cell in the window (general affine).
    nrows, ncols = data.shape
    col_centres = (np.arange(ncols, dtype=np.float64) + 0.5)[np.newaxis, :]
    row_centres = (np.arange(nrows, dtype=np.float64) + 0.5)[:, np.newaxis]
    xs = transform.a * col_centres + transform.b * row_centres + transform.c
    ys = transform.d * col_centres + transform.e * row_centres + transform.f

    inside = shapely.contains_xy(polygon, xs, ys)

    if nodata is not None:
        if np.issubdtype(data.dtype, np.floating) and math.isnan(float(nodata)):
            valid = ~np.isnan(data)
        else:
            valid = data != nodata
        inside &= valid

    values = data[inside]
    if values.size == 0:
        return None
    return float(np.mean(values, dtype=np.float64))
```