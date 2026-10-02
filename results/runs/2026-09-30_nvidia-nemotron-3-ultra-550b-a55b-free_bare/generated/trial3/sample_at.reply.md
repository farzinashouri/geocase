```python
import rasterio
from rasterio.warp import transform
from rasterio.errors import RasterioIOError
import numpy as np


def sample_at(raster_path: str, lon: float, lat: float) -> float | None:
    """
    Sample a single-band GeoTIFF at the given WGS84 (EPSG:4326) coordinates.

    Args:
        raster_path: Path to the GeoTIFF file.
        lon: Longitude in degrees (WGS84).
        lat: Latitude in degrees (WGS84).

    Returns:
        The raster value as a float, or None if the location is outside the
        raster extent or falls on a nodata pixel.
    """
    try:
        with rasterio.open(raster_path) as src:
            if src.count != 1:
                raise ValueError("Expected a single-band raster")

            # Transform WGS84 (lon, lat) to the raster's CRS
            xs, ys = transform("EPSG:4326", src.crs, [lon], [lat])
            x, y = xs[0], ys[0]

            # Check if the point is within the raster bounds
            if not (src.bounds.left <= x <= src.bounds.right and
                    src.bounds.bottom <= y <= src.bounds.top):
                return None

            # Sample the value at the transformed coordinates
            # rasterio.sample expects (x, y) tuples
            values = list(src.sample([(x, y)]))
            if not values:
                return None

            val = values[0][0]

            # Handle nodata
            if src.nodata is not None:
                if isinstance(val, float) and np.isnan(val):
                    return None
                if val == src.nodata:
                    return None

            return float(val)

    except RasterioIOError:
        raise FileNotFoundError(f"Could not open raster: {raster_path}")
```