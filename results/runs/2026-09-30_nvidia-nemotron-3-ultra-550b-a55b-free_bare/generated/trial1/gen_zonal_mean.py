import rasterio
from rasterio.mask import mask
import numpy as np

def zonal_mean(raster_path, polygon):
    """
    Compute the mean of pixel values whose centers fall inside the given polygon.

    Parameters
    ----------
    raster_path : str
        Path to a single-band GeoTIFF file.
    polygon : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Polygon in the same CRS as the raster.

    Returns
    -------
    float or None
        Mean of valid pixel values inside the polygon, or None if no valid pixels.
    """
    with rasterio.open(raster_path) as src:
        if src.count != 1:
            raise ValueError("Raster must have exactly one band.")
        nodata = src.nodata

        # Mask the raster with the polygon. all_touched=False (default) selects
        # pixels whose centers are inside the polygon.
        masked_arr, _, _ = mask(src, [polygon], crop=False, all_touched=False)

        # masked_arr is a 3D masked array (1, height, width)
        data = masked_arr[0]
        geom_mask = masked_arr.mask[0]

        # Exclude nodata values from the calculation
        if nodata is not None:
            valid_mask = ~geom_mask & (data != nodata)
        else:
            valid_mask = ~geom_mask

        valid_data = data[valid_mask]
        if valid_data.size == 0:
            return None

        return float(np.mean(valid_data))