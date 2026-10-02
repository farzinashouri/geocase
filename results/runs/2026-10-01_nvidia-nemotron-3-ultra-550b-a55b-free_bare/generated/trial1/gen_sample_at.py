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
        if not (src.bounds.left <= x <= src.bounds.right and src.bounds.bottom <= y <= src.bounds.top):
            return None

        # Sample the raster at the transformed coordinates
        # Using sample with indexes=[1] for single band
        values = list(src.sample([(x, y)], indexes=[1], resampling=Resampling.nearest))

        if not values:
            return None

        val = values[0][0]

        # Check for nodata
        if src.nodata is not None:
            if isinstance(val, float) and np.isnan(val):
                return None
            if val == src.nodata:
                return None

        return float(val)