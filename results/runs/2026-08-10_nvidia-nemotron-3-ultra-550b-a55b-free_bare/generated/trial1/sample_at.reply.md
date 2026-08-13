```python
import rasterio
from rasterio.warp import transform
import numpy as np


def sample_at(raster_path, lon, lat):
    """
    Sample a single-band GeoTIFF at the given WGS84 longitude/latitude.

    Args:
        raster_path: Path to the GeoTIFF file.
        lon: Longitude in WGS84 (EPSG:4326).
        lat: Latitude in WGS84 (EPSG:4326).

    Returns:
        The raster value as a float, or None if the location has no data.
    """
    with rasterio.open(raster_path) as src:
        # Transform WGS84 coordinates to the raster's CRS
        xs, ys = transform('EPSG:4326', src.crs, [lon], [lat])
        x, y = xs[0], ys[0]

        # Sample the raster at the transformed coordinates
        values = list(src.sample([(x, y)]))

        if not values:
            return None

        val = values[0][0]

        # Check for nodata
        if src.nodata is not None:
            if isinstance(val, float) and (np.isnan(val) or val == src.nodata):
                return None
            elif val == src.nodata:
                return None

        return float(val)
```