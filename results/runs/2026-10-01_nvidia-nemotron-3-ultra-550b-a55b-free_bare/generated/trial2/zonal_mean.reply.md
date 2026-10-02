```python
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.features import geometry_mask
import numpy as np
from shapely.geometry import BaseGeometry

def zonal_mean(raster_path: str, polygon: BaseGeometry) -> float | None:
    """
    Compute the mean of pixel values in a single-band GeoTIFF whose centers fall inside a polygon.

    Parameters
    ----------
    raster_path : str
        Path to the GeoTIFF file.
    polygon : shapely.geometry.BaseGeometry
        Polygon in the raster's coordinate reference system.

    Returns
    -------
    float or None
        Mean of valid pixel values, or None if no valid pixels are inside the polygon.
    """
    with rasterio.open(raster_path) as src:
        # Window covering the polygon's bounding box
        window = from_bounds(*polygon.bounds, transform=src.transform)
        window = window.round_offsets().round_shape()
        window = window.intersection(Window(0, 0, src.width, src.height))
        if window.width <= 0 or window.height <= 0:
            return None

        # Read the band data for the window
        data = src.read(1, window=window)
        window_transform = src.window_transform(window)

        # Mask for pixels with centers inside the polygon
        inside_mask = geometry_mask(
            [polygon],
            out_shape=(window.height, window.width),
            transform=window_transform,
            invert=True,
            all_touched=False
        )

        # Mask for valid (non-nodata) pixels
        nodata = src.nodata
        if nodata is not None:
            if isinstance(nodata, float) and np.isnan(nodata):
                valid_data_mask = ~np.isnan(data)
            else:
                valid_data_mask = data != nodata
        else:
            valid_data_mask = np.ones_like(data, dtype=bool)

        combined_mask = inside_mask & valid_data_mask
        if not combined_mask.any():
            return None

        return float(np.mean(data[combined_mask]))
```