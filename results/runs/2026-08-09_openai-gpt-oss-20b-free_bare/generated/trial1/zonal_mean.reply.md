```python
import rasterio
import numpy as np
from rasterio.features import rasterize
from shapely.geometry import Polygon


def zonal_mean(raster_path: str, polygon: Polygon) -> float | None:
    """
    Compute the mean of raster pixel values whose centres fall inside the given polygon.

    Parameters
    ----------
    raster_path : str
        Path to a single-band GeoTIFF.
    polygon : shapely.geometry.Polygon
        Polygon expressed in the raster's CRS.

    Returns
    -------
    float | None
        Mean of valid pixel values inside the polygon, or None if no such pixels exist.
    """
    with rasterio.open(raster_path) as src:
        # Read the first (and only) band into memory
        data = src.read(1)
        nodata = src.nodata

        # Rasterize the polygon onto the raster grid.
        # all_touched=False ensures only pixels whose centre lies inside the polygon are set.
        mask = rasterize(
            [(polygon, 1)],
            out_shape=data.shape,
            transform=src.transform,
            fill=0,
            dtype="uint8",
            all_touched=False,
        ).astype(bool)

        # Exclude nodata values if defined
        if nodata is not None:
            mask &= data != nodata

        # Extract the values that are both inside the polygon and valid
        values = data[mask]

        if values.size == 0:
            return None

        return float(values.mean())
```