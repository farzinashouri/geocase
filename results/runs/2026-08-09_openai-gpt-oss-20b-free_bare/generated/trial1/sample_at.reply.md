```python
import rasterio
from rasterio.windows import Window
import pyproj
import numpy as np


def sample_at(raster_path: str, lon: float, lat: float) -> float | None:
    """
    Return the raster value at the given WGS84 longitude/latitude.

    Parameters
    ----------
    raster_path : str
        Path to a single‑band GeoTIFF.
    lon : float
        Longitude in WGS84.
    lat : float
        Latitude in WGS84.

    Returns
    -------
    float | None
        The raster value at the point, or None if the point is outside the
        raster bounds or the raster has no data at that location.
    """
    with rasterio.open(raster_path) as src:
        # Transform WGS84 coordinates to the raster's CRS
        transformer = pyproj.Transformer.from_crs(
            "EPSG:4326", src.crs, always_xy=True
        )
        x, y = transformer.transform(lon, lat)

        # Check if the point lies within the raster bounds
        if not (
            src.bounds.left <= x <= src.bounds.right
            and src.bounds.bottom <= y <= src.bounds.top
        ):
            return None

        # Get the row/column indices of the pixel containing the point
        row, col = src.index(x, y)

        # Read the single pixel as a masked array
        window = Window(col, row, 1, 1)
        data = src.read(1, window=window, masked=True)

        # If the pixel is masked (nodata or NaN), return None
        if data.mask[0, 0]:
            return None

        # Return the value as a float
        return float(data[0, 0])
```