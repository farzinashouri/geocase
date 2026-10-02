```python
import rasterio
import numpy as np
from shapely.vectorized import contains

def zonal_mean(raster_path, polygon):
    """
    Compute the mean of pixel values whose centers fall inside a polygon.

    Parameters
    ----------
    raster_path : str
        Path to a single-band GeoTIFF file.
    polygon : shapely.geometry.Polygon
        Polygon in the same CRS as the raster.

    Returns
    -------
    float or None
        Mean of valid pixel values inside the polygon, or None if no such pixels exist.
    """
    with rasterio.open(raster_path) as src:
        band = src.read(1)
        nodata = src.nodata
        transform = src.transform
        height, width = band.shape

        # Generate row and column indices for all pixels
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')

        # Compute the coordinates of pixel centers
        xs, ys = rasterio.transform.xy(transform, rows, cols, offset='center')

        # Determine which pixel centers lie inside the polygon
        inside = contains(polygon, xs, ys)

        # Mask out nodata values
        if nodata is not None:
            valid = (band != nodata)
        else:
            valid = np.ones_like(band, dtype=bool)

        # Combine masks
        mask = inside & valid

        if not mask.any():
            return None

        return float(np.mean(band[mask]))
```