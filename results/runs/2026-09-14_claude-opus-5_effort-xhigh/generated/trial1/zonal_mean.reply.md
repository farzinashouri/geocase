```python
"""Zonal statistics for a single-band raster.

``zonal_mean`` averages the pixels of a GeoTIFF whose centres fall inside a
polygon given in the raster's own CRS.  Importing this module has no side
effects.
"""

from __future__ import annotations

import math
import os
from typing import Optional, Union

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window
from shapely.geometry.base import BaseGeometry

__all__ = ["zonal_mean"]


def _pixel_window(dataset, bounds) -> Optional[Window]:
    """Smallest in-range pixel window covering ``bounds`` (raster CRS).

    Uses the inverse geotransform on the corners of the bounding box, so it is
    also correct for rotated/sheared transforms.  One pixel of margin is added
    so that floating-point rounding can never drop a boundary pixel; the window
    is only a read optimisation, the point-in-polygon test below decides
    membership.  Returns ``None`` when the box misses the raster entirely.
    """
    minx, miny, maxx, maxy = bounds
    inverse = ~dataset.transform
    corners = [inverse * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
    cols = [col for col, _ in corners]
    rows = [row for _, row in corners]

    col_off = max(0, math.floor(min(cols)) - 1)
    row_off = max(0, math.floor(min(rows)) - 1)
    col_end = min(dataset.width, math.ceil(max(cols)) + 1)
    row_end = min(dataset.height, math.ceil(max(rows)) + 1)
    if col_end <= col_off or row_end <= row_off:
        return None
    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def zonal_mean(
    raster_path: Union[str, os.PathLike],
    polygon: BaseGeometry,
) -> Optional[float]:
    """Mean of the band-1 pixels whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path to a single-band GeoTIFF.
    polygon:
        Shapely (Multi)Polygon, already expressed in the raster's CRS.  No
        reprojection is attempted.

    Returns
    -------
    float or None
        The unweighted mean of the selected pixel values, or ``None`` if no
        valid pixel centre lies inside the polygon.

    Notes
    -----
    * A pixel is selected when its *centre* is strictly inside the polygon;
      centres lying exactly on the boundary are excluded, as are pixels equal
      to the raster's nodata value (and pixels masked out by an internal or
      alpha mask band).
    * Non-finite values (NaN/inf) in float rasters are treated as invalid too,
      so a stray NaN cannot poison the result.
    * Every pixel counts equally: no partial-overlap area weighting.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as dataset:
        window = _pixel_window(dataset, polygon.bounds)
        if window is None:
            return None
        band = dataset.read(1, window=window, masked=True)
        transform = dataset.window_transform(window)

    values = np.asarray(band.data)
    valid = ~np.ma.getmaskarray(band)
    if np.issubdtype(values.dtype, np.floating):
        valid &= np.isfinite(values)
    if not valid.any():
        return None

    # Centres of the valid pixels only, in the raster CRS.
    rows, cols = np.nonzero(valid)
    centre_cols = cols + 0.5
    centre_rows = rows + 0.5
    xs = transform.a * centre_cols + transform.b * centre_rows + transform.c
    ys = transform.d * centre_cols + transform.e * centre_rows + transform.f

    shapely.prepare(polygon)  # caches an index; semantics are unchanged
    inside = shapely.contains_xy(polygon, xs, ys)
    if not inside.any():
        return None

    selected = values[rows[inside], cols[inside]]
    return float(np.mean(selected, dtype=np.float64))
```