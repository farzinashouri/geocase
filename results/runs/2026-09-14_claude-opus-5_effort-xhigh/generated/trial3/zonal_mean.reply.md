```python
"""Zonal statistics for a single-band raster.

``zonal_mean`` averages the pixels of a GeoTIFF whose centres fall inside a
polygon given in the raster's own CRS. No reprojection is performed.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window

# Upper bound on the number of pixels held in memory at once, so that a polygon
# spanning a large raster is processed in row chunks rather than in one read.
_MAX_CHUNK_PIXELS = 4_000_000


def zonal_mean(raster_path, polygon) -> Optional[float]:
    """Mean of band 1 over the pixels whose centres lie inside ``polygon``.

    Parameters
    ----------
    raster_path:
        Path (or any object rasterio can open) of a single-band GeoTIFF.
    polygon:
        A shapely Polygon or MultiPolygon expressed in the raster's CRS.

    A pixel contributes when its centre is strictly inside the polygon
    (centres exactly on the boundary are excluded) and its value differs from
    the raster's nodata value. NaN is always treated as nodata for float
    rasters. Returns ``None`` when no such pixel exists.
    """
    if polygon is None or polygon.is_empty:
        return None

    total = 0.0
    count = 0

    with rasterio.open(raster_path) as src:
        extent = _bounds_extent(src, polygon.bounds)
        if extent is None:
            return None
        row_start, row_stop, col_start, col_stop = extent

        transform = src.transform
        nodata = src.nodata
        # Prepare once: the point-in-polygon test below runs per chunk.
        shapely.prepare(polygon)

        width = col_stop - col_start
        chunk_height = max(1, min(row_stop - row_start, _MAX_CHUNK_PIXELS // width))

        for row_off in range(row_start, row_stop, chunk_height):
            height = min(chunk_height, row_stop - row_off)
            data = src.read(1, window=Window(col_start, row_off, width, height))

            valid = _valid_mask(data, nodata)
            if not valid.any():
                continue

            # Only valid pixels are tested against the polygon.
            rows, cols = np.nonzero(valid)
            xs, ys = _pixel_centres(transform, rows + row_off, cols + col_start)
            inside = shapely.contains_xy(polygon, xs, ys)
            if not inside.any():
                continue

            values = data[rows[inside], cols[inside]].astype("float64", copy=False)
            total += float(values.sum())
            count += int(values.size)

    if count == 0:
        return None
    return total / count


def _bounds_extent(src, bounds):
    """Row/column half-open extent covering ``bounds``, clipped to the raster.

    Returns ``None`` when the polygon's bounding box misses the raster. The
    extent is padded by one pixel so that float rounding can never drop a
    pixel whose centre is inside the polygon; surplus pixels are discarded by
    the point-in-polygon test.
    """
    minx, miny, maxx, maxy = bounds
    inverse = ~src.transform

    cols, rows = [], []
    for corner in ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)):
        col, row = inverse * corner
        cols.append(col)
        rows.append(row)

    col_start = max(0, int(math.floor(min(cols))) - 1)
    col_stop = min(src.width, int(math.ceil(max(cols))) + 1)
    row_start = max(0, int(math.floor(min(rows))) - 1)
    row_stop = min(src.height, int(math.ceil(max(rows))) + 1)

    if col_stop <= col_start or row_stop <= row_start:
        return None
    return row_start, row_stop, col_start, col_stop


def _valid_mask(data, nodata):
    """Boolean mask of the pixels that carry a real value."""
    valid = np.ones(data.shape, dtype=bool)
    if np.issubdtype(data.dtype, np.floating):
        valid &= ~np.isnan(data)
    if nodata is not None and not (isinstance(nodata, float) and math.isnan(nodata)):
        valid &= data != nodata
    return valid


def _pixel_centres(transform, rows, cols):
    """Map integer pixel indices to centre coordinates, rotation included."""
    c = cols.astype("float64") + 0.5
    r = rows.astype("float64") + 0.5
    xs = transform.a * c + transform.b * r + transform.c
    ys = transform.d * c + transform.e * r + transform.f
    return xs, ys
```