"""Module for sampling raster values at geographic coordinates."""

import rasterio
from rasterio.warp import transform
from rasterio.enums import Resampling
import numpy as np


def sample_at(raster_path: str, lon: float, lat: float) -> float | None:
    """
    Sample a single-band GeoTIFF at the given WGS84 longitude/latitude.

    Args:
        raster_path: Path to the GeoTIFF file.
        lon: Longitude in WGS84 (EPSG:4326).
        lat: Latitude in WGS84 (EPSG:4326).

    Returns:
        The raster value as a float, or None if the location falls on nodata
        or outside the raster extent.
    """
    with rasterio.open(raster_path) as src:
        # Transform WGS84 coordinates to the raster's CRS
        xs, ys = transform("EPSG:4326", src.crs, [lon], [lat])
        x, y = xs[0], ys[0]

        # Check if the point is within the raster bounds
        if not (src.bounds.left <= x <= src.bounds.right and
                src.bounds.bottom <= y <= src.bounds.top):
            return None

        # Convert to pixel coordinates (row, col)
        row, col = src.index(x, y)

        # Check if pixel coordinates are valid
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        # Read the single pixel value
        # Using window to read just one pixel efficiently
        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(1, window=window, resampling=Resampling.nearest)

        if data.size == 0:
            return None

        value = data[0, 0]

        # Check for nodata
        if src.nodata is not None:
            if np.issubdtype(data.dtype, np.floating):
                if np.isnan(value) or value == src.nodata:
                    return None
            else:
                if value == src.nodata:
                    return None

        return float(value)