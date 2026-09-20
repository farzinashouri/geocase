```python
"""Zonal statistics for a single-band raster and a polygon in the raster's CRS.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

import numpy as np
import rasterio
from rasterio.transform import xy as _transform_xy
from rasterio.windows import Window
from shapely import contains_xy

__all__ = ["zonal_mean"]

# Number of raster rows read at a time, to bound peak memory on large zones.
_ROW_BLOCK = 512


def _bbox_window(src, bounds):
    """Smallest pixel window of ``src`` that can contain the bbox ``bounds``.

    Works for rotated transforms too, because the four bbox corners are mapped
    individually into pixel space. Returns ``None`` if the bbox misses the
    raster entirely.
    """
    minx, miny, maxx, maxy = bounds
    inv = ~src.transform
    cols, rows = zip(
        *(
            inv * (x, y)
            for x, y in ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy))
        )
    )

    # One pixel of slack so that centres on the very edge are never dropped.
    col_off = max(0, int(math.floor(min(cols))) - 1)
    row_off = max(0, int(math.floor(min(rows))) - 1)
    col_end = min(src.width, int(math.ceil(max(cols))) + 1)
    row_end = min(src.height, int(math.ceil(max(rows))) + 1)

    if col_end <= col_off or row_end <= row_off:
        return None
    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def zonal_mean(raster_path, polygon):
    """Mean of band 1 over pixels whose centres lie inside ``polygon``.

    Parameters
    ----------
    raster_path : str or os.PathLike
        Path to a single-band GeoTIFF.
    polygon : shapely.geometry.base.BaseGeometry
        Polygon (or multi-polygon) expressed in the raster's own CRS.

    Returns
    -------
    float or None
        The mean of the valid pixel values whose centres fall strictly inside
        the polygon, or ``None`` if there are no such pixels. Pixels equal to
        the raster's nodata value (and non-finite values in float rasters) are
        excluded.
    """
    if polygon is None or polygon.is_empty:
        return None

    total = 0.0
    count = 0

    with rasterio.open(raster_path) as src:
        window = _bbox_window(src, polygon.bounds)
        if window is None:
            return None

        is_float = np.issubdtype(np.dtype(src.dtypes[0]), np.floating)
        col_indices = np.arange(window.width)

        for block_off in range(0, int(window.height), _ROW_BLOCK):
            block_height = min(_ROW_BLOCK, int(window.height) - block_off)
            block = Window(
                window.col_off, window.row_off + block_off, window.width, block_height
            )

            data = src.read(1, window=block, masked=True)
            if data.size == 0:
                continue

            rows, cols = np.meshgrid(
                np.arange(block_height), col_indices, indexing="ij"
            )
            xs, ys = _transform_xy(
                src.window_transform(block), rows, cols, offset="center"
            )
            xs = np.asarray(xs, dtype="float64").reshape(data.shape)
            ys = np.asarray(ys, dtype="float64").reshape(data.shape)

            valid = contains_xy(polygon, xs, ys) & ~np.ma.getmaskarray(data)
            if not valid.any():
                continue

            values = np.asarray(data.data[valid], dtype="float64")
            if is_float:
                values = values[np.isfinite(values)]
                if values.size == 0:
                    continue

            total += float(values.sum())
            count += int(values.size)

    if count == 0:
        return None
    return total / count
```