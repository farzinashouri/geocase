```python
"""Zonal mean of a single-band raster over a polygon given in the raster's CRS.

A pixel contributes to the mean when its *centre* lies inside the polygon
(strict containment: centres exactly on the polygon boundary are excluded) and
its value is neither the raster's nodata value nor NaN.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window

__all__ = ["zonal_mean"]

# Upper bound on the number of pixels held in memory at once, so that a polygon
# covering a very large raster is processed in row chunks instead of one read.
_MAX_PIXELS_PER_CHUNK = 4_000_000


def _bbox_window(transform, width, height, bounds):
    """Pixel-space bounds (row_start, row_stop, col_start, col_stop) covering
    the geometry's bounding box, clipped to the raster. ``None`` if disjoint.

    The four bbox corners are pushed through the inverse transform, so rotated
    (non north-up) transforms are handled too. One pixel of padding absorbs
    floating-point error at the edges; padding can only add candidate pixels,
    never change which centres test as inside.
    """
    minx, miny, maxx, maxy = bounds
    inverse = ~transform
    corners = [inverse * (x, y) for x in (minx, maxx) for y in (miny, maxy)]
    cols = [col for col, _ in corners]
    rows = [row for _, row in corners]

    col_start = max(0, int(math.floor(min(cols))) - 1)
    col_stop = min(width, int(math.ceil(max(cols))) + 1)
    row_start = max(0, int(math.floor(min(rows))) - 1)
    row_stop = min(height, int(math.ceil(max(rows))) + 1)

    if col_start >= col_stop or row_start >= row_stop:
        return None
    return row_start, row_stop, col_start, col_stop


def zonal_mean(raster_path, polygon):
    """Mean of the band-1 pixels whose centres fall inside ``polygon``.

    Parameters
    ----------
    raster_path : str or os.PathLike
        Path to a single-band GeoTIFF.
    polygon : shapely.geometry.base.BaseGeometry
        Polygon (or MultiPolygon) expressed in the raster's own CRS.

    Returns
    -------
    float or None
        The mean of the selected valid pixel values, or ``None`` when no pixel
        with a valid value has its centre inside the polygon.
    """
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        extent = _bbox_window(src.transform, src.width, src.height, polygon.bounds)
        if extent is None:
            return None
        row_start, row_stop, col_start, col_stop = extent

        n_cols = col_stop - col_start
        chunk_rows = max(1, _MAX_PIXELS_PER_CHUNK // n_cols)

        transform = src.transform
        col_centres = np.arange(col_start, col_stop, dtype="float64") + 0.5

        shapely.prepare(polygon)  # speeds up the repeated point-in-polygon tests

        total = 0.0
        count = 0
        for chunk_start in range(row_start, row_stop, chunk_rows):
            chunk_stop = min(chunk_start + chunk_rows, row_stop)
            window = Window(
                col_start, chunk_start, n_cols, chunk_stop - chunk_start
            )
            # masked=True applies the nodata value and any internal mask band.
            band = src.read(1, window=window, masked=True)
            invalid = np.ma.getmaskarray(band)
            if invalid.all():
                continue

            row_centres = np.arange(chunk_start, chunk_stop, dtype="float64") + 0.5
            cols, rows = np.meshgrid(col_centres, row_centres)
            xs = transform.a * cols + transform.b * rows + transform.c
            ys = transform.d * cols + transform.e * rows + transform.f

            values = np.asarray(band.data, dtype="float64")
            selected = shapely.contains_xy(polygon, xs, ys)
            selected &= ~invalid
            selected &= ~np.isnan(values)  # NaN used as a nodata marker
            if not selected.any():
                continue

            total += float(values[selected].sum(dtype="float64"))
            count += int(selected.sum())

    if count == 0:
        return None
    return total / count
```