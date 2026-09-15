```python
"""Zonal statistics for a single-band raster.

Exposes :func:`zonal_mean`, the mean of the values of a single-band GeoTIFF
over the pixels whose centres fall inside a polygon expressed in the raster's
own coordinate reference system.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window

# Upper bound on the pixels held in memory per read. The polygon's bounding box
# may cover an arbitrarily large part of the raster, so the read is chunked
# into row strips to keep peak memory bounded.
_MAX_BLOCK_PIXELS = 4_000_000


def zonal_mean(
    raster_path: str | os.PathLike[str],
    polygon: shapely.Geometry,
) -> float | None:
    """Mean of the pixels of a single-band raster inside ``polygon``.

    A pixel contributes when its centre lies strictly inside ``polygon`` (a
    centre exactly on the boundary is excluded) and its value is not the
    raster's nodata value. NaN is always treated as missing in floating-point
    rasters, since it cannot be averaged.

    Args:
        raster_path: Path to a single-band GeoTIFF; the first band is read.
        polygon: Shapely geometry in the same CRS as the raster. No
            reprojection is performed.

    Returns:
        The mean as a ``float``, or ``None`` if no pixel with a valid value has
        its centre inside ``polygon``.
    """
    if polygon is None or polygon.is_empty:
        return None

    total = 0.0
    count = 0

    with rasterio.open(raster_path) as src:
        col_start, row_start, col_stop, row_stop = _candidate_pixels(src, polygon)
        if col_start >= col_stop or row_start >= row_stop:
            return None

        nodata = src.nodata
        # Caches a prepared geometry on ``polygon``, which makes the many
        # point-in-polygon tests below much cheaper.
        shapely.prepare(polygon)

        width = col_stop - col_start
        block_height = max(1, _MAX_BLOCK_PIXELS // width)
        for row_off in range(row_start, row_stop, block_height):
            window = Window(
                col_off=col_start,
                row_off=row_off,
                width=width,
                height=min(block_height, row_stop - row_off),
            )
            data = src.read(1, window=window)

            rows, cols = np.nonzero(_valid_mask(data, nodata))
            if rows.size == 0:
                continue

            xs, ys = _pixel_centres(src.window_transform(window), rows, cols)
            inside = shapely.contains_xy(polygon, xs, ys)
            if not inside.any():
                continue

            total += float(data[rows, cols][inside].sum(dtype=np.float64))
            count += int(np.count_nonzero(inside))

    if count == 0:
        return None
    return total / count


def _candidate_pixels(
    src: rasterio.DatasetReader,
    geometry: shapely.Geometry,
) -> tuple[int, int, int, int]:
    """Half-open pixel index range ``(col_start, row_start, col_stop, row_stop)``.

    The range is a deliberately generous superset of the geometry's bounding
    box -- one pixel of padding on every side, clipped to the raster -- because
    membership is decided exactly by the point-in-polygon test; a handful of
    extra candidate pixels only costs a few predicate evaluations. Mapping all
    four bounding-box corners through the inverse transform keeps this correct
    for rotated transforms too.
    """
    inverse = ~src.transform
    minx, miny, maxx, maxy = geometry.bounds
    pixels = [
        inverse * corner
        for corner in ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy))
    ]
    cols = [col for col, _ in pixels]
    rows = [row for _, row in pixels]

    col_start = max(0, int(np.floor(min(cols))) - 1)
    col_stop = min(src.width, int(np.ceil(max(cols))) + 1)
    row_start = max(0, int(np.floor(min(rows))) - 1)
    row_stop = min(src.height, int(np.ceil(max(rows))) + 1)
    return col_start, row_start, col_stop, row_stop


def _valid_mask(data: np.ndarray, nodata: float | None) -> np.ndarray:
    """Boolean mask of the pixels of ``data`` that carry a real value."""
    if np.issubdtype(data.dtype, np.floating):
        valid = ~np.isnan(data)
        if nodata is not None and not np.isnan(nodata):
            valid &= data != nodata
        return valid
    if nodata is None:
        return np.ones(data.shape, dtype=bool)
    return data != nodata


def _pixel_centres(
    transform,
    rows: np.ndarray,
    cols: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Map window-relative pixel indices to their centre coordinates."""
    col_centres = cols + 0.5
    row_centres = rows + 0.5
    xs = transform.c + transform.a * col_centres + transform.b * row_centres
    ys = transform.f + transform.d * col_centres + transform.e * row_centres
    return xs, ys
```