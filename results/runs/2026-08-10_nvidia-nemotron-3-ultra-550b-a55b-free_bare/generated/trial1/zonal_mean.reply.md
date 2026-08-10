```python
import rasterio
from rasterio.features import geometry_mask
import numpy as np
from typing import Optional
from shapely.geometry import BaseGeometry

def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    """
    Compute the mean of raster values for pixels whose centers fall inside a polygon.

    Parameters
    ----------
    raster_path : str
        Path to a single-band GeoTIFF file.
    polygon : shapely.geometry.BaseGeometry
        A polygon in the same CRS as the raster. Only pixels with centers inside
        this polygon are considered.

    Returns
    -------
    float or None
        The mean of valid pixel values, or None if no valid pixel centers lie
        inside the polygon.
    """
    with rasterio.open(raster_path) as src:
        # Read the first band as a masked array (nodata values are masked)
        data = src.read(1, masked=True)
        transform = src.transform

        # Create a boolean mask where True indicates the pixel center is inside the polygon
        # all_touched=False ensures only pixels with centers inside are included
        inside_mask = geometry_mask(
            [polygon],
            out_shape=data.shape,
            transform=transform,
            all_touched=False,
            invert=True
        )

        # Combine with the data's validity mask (True where data is valid)
        valid_mask = inside_mask & (~data.mask)

        if not valid_mask.any():
            return None

        # Compute mean of valid pixels
        return float(data[valid_mask].mean())
```