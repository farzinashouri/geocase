import rasterio
from rasterio.features import rasterize
import numpy as np
from shapely.geometry import Polygon, MultiPolygon


def zonal_mean(raster_path: str, polygon: Polygon | MultiPolygon) -> float | None:
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
        # Read the first band
        band = src.read(1)
        nodata = src.nodata
        transform = src.transform
        height, width = band.shape

        # Mask of valid data (exclude nodata)
        if nodata is not None:
            valid_mask = band != nodata
        else:
            valid_mask = np.ones_like(band, dtype=bool)

        # Rasterize the polygon to get a mask of pixels whose centers are inside
        # all_touched=False uses the pixel center rule
        polygon_mask = rasterize(
            [polygon],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.uint8,
            all_touched=False,
        ).astype(bool)

        # Combine masks
        combined_mask = valid_mask & polygon_mask

        # Extract values
        values = band[combined_mask]

        if values.size == 0:
            return None

        return float(np.mean(values))