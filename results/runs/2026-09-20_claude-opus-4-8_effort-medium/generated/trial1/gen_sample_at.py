"""Sample a single-band GeoTIFF at a WGS84 coordinate."""

from __future__ import annotations

import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    """Return the band-1 value of a single-band GeoTIFF at the given WGS84
    longitude/latitude, or ``None`` if there is no data at that location.

    The raster may be in any CRS; the input coordinate is reprojected into
    the raster's CRS before sampling. ``None`` is returned when the point
    falls outside the raster or lands on a nodata cell.
    """
    with rasterio.open(raster_path) as dataset:
        # Reproject the WGS84 point into the raster's CRS (if it has one).
        if dataset.crs is not None:
            transformer = Transformer.from_crs(
                "EPSG:4326", dataset.crs, always_xy=True
            )
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        # Reject non-finite results of the transform.
        if not (_isfinite(x) and _isfinite(y)):
            return None

        # Bounds check in raster CRS coordinates.
        left, bottom, right, top = dataset.bounds
        if not (left <= x <= right and bottom <= y <= top):
            return None

        # Map to row/col and guard against off-by-one at the edges.
        row, col = dataset.index(x, y)
        if not (0 <= row < dataset.height and 0 <= col < dataset.width):
            return None

        window = ((row, row + 1), (col, col + 1))
        value = dataset.read(1, window=window)[0, 0]

        nodata = dataset.nodata
        if nodata is not None:
            if value == nodata:
                return None
            # nodata may itself be NaN.
            if not _isfinite(nodata) and not _isfinite(value):
                return None

        # A NaN pixel value represents missing data.
        if not _isfinite(value):
            return None

        return float(value)


def _isfinite(v):
    try:
        return v == v and v not in (float("inf"), float("-inf"))
    except TypeError:
        return False