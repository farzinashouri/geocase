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
        Float value at the location, or None if the point is outside the raster
        extent or the raster reports nodata at that pixel.
    """
    with rasterio.open(raster_path) as src:
        # Transform from WGS84 to the raster's CRS
        xs, ys = transform("EPSG:4326", src.crs, [lon], [lat])
        x, y = xs[0], ys[0]

        # Quick bounds check
        if not (src.bounds.left <= x <= src.bounds.right and src.bounds.bottom <= y <= src.bounds.top):
            return None

        # Sample the first (and only) band at the transformed coordinates
        # src.sample returns a generator of arrays, one per band
        try:
            values = next(src.sample([(x, y)]))
        except (StopIteration, IndexError):
            return None

        val = values[0]

        # Nodata handling
        nodata = src.nodata
        if nodata is not None:
            if isinstance(nodata, float) and np.isnan(nodata):
                if np.isnan(val):
                    return None
            elif val == nodata:
                return None

        return float(val)