```python
import rasterio
from rasterio.features import geometry_mask
import numpy as np

def zonal_mean(raster_path, polygon):
    """
    Compute the mean of pixel values whose centers fall inside a polygon.

    Parameters
    ----------
    raster_path : str
        Path to a single-band GeoTIFF file.
    polygon : shapely.geometry.BaseGeometry
        A polygon in the same CRS as the raster.

    Returns
    -------
    float or None
        Mean of valid pixel values inside the polygon, or None if no valid pixels.
    """
    with rasterio.open(raster_path) as src:
        # Read band 1 as a masked array (nodata values are masked)
        data_masked = src.read(1, masked=True)
        transform = src.transform
        height, width = src.height, src.width

        # Mask of pixels whose centers are inside the polygon
        # geometry_mask returns True for pixels NOT covered when invert=False (default)
        # We set invert=True so that True means covered (center inside polygon)
        inside_mask = geometry_mask(
            [polygon],
            out_shape=(height, width),
            transform=transform,
            invert=True
        )

        # Combine with nodata mask: valid pixels are inside AND not masked (i.e., not nodata)
        # data_masked.mask is True for nodata pixels; we want the opposite
        if np.ma.is_masked(data_masked):
            valid_mask = inside_mask & (~data_masked.mask)
        else:
            # No masked values (no nodata present)
            valid_mask = inside_mask

        if not np.any(valid_mask):
            return None

        # Extract valid data values and compute mean
        valid_data = data_masked.data[valid_mask]
        return float(np.mean(valid_data))
```