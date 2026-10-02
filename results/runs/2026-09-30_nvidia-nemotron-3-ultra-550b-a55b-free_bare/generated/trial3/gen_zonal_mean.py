import rasterio
from rasterio.features import geometry_mask
import numpy as np


def zonal_mean(raster_path, polygon):
    """
    Compute the mean of pixel values whose centers fall inside the given polygon.

    Parameters
    ----------
    raster_path : str
        Path to a single-band GeoTIFF file.
    polygon : shapely.geometry.BaseGeometry
        A polygon (or multipolygon) in the same CRS as the raster.

    Returns
    -------
    float or None
        The mean of valid pixel values inside the polygon, or None if no valid pixels.
    """
    with rasterio.open(raster_path) as src:
        # Read the first (and only) band
        band = src.read(1)
        nodata = src.nodata
        transform = src.transform

        # Create a mask where True indicates pixel centers inside the polygon
        inside_mask = geometry_mask(
            [polygon],
            out_shape=band.shape,
            transform=transform,
            all_touched=False,  # use pixel centers
            invert=True         # True for inside
        )

        # Valid data mask: exclude nodata
        if nodata is not None:
            valid_mask = (band != nodata) & inside_mask
        else:
            valid_mask = inside_mask

        # Extract valid values
        values = band[valid_mask]

        if values.size == 0:
            return None

        return float(np.mean(values))