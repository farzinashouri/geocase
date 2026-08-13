```python
import rasterio
import rasterio.mask


def zonal_mean(raster_path, polygon):
    """
    Compute the mean of raster values whose pixel centres lie within the given polygon.

    Parameters
    ----------
    raster_path : str or pathlib.Path
        Path to a single‑band GeoTIFF.
    polygon : shapely.geometry.base.BaseGeometry
        Polygon expressed in the raster's CRS.

    Returns
    -------
    float or None
        Mean of valid pixel values inside the polygon, or None if no valid pixel.
    """
    with rasterio.open(raster_path) as src:
        if src.count < 1:
            raise ValueError("Raster must contain at least one band")

        nodata = src.nodata
        out_image, _ = rasterio.mask.mask(
            src,
            [polygon],
            crop=False,
            all_touched=False,
            nodata=nodata,
        )
        data = out_image[0]  # first (and only) band

        # If all values are masked (outside polygon or nodata), return None
        if data.mask.all():
            return None

        return float(data.mean())
```