```python
"""Sample a single-band GeoTIFF at a WGS84 coordinate."""

import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    """Return the raster value at WGS84 (lon, lat), or None if nodata.

    Opens a single-band GeoTIFF (in any CRS), reprojects the given
    WGS84 longitude/latitude into the raster's CRS, and samples the
    band. Returns the value as a float, or None when the location
    falls outside the raster or hits a nodata pixel.
    """
    with rasterio.open(raster_path) as src:
        # Reproject the query point from WGS84 into the raster's CRS.
        transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        # Convert map coordinates to row/col indices.
        row, col = src.index(x, y)

        # Reject points outside the raster extent.
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None

        window = ((row, row + 1), (col, col + 1))
        value = src.read(1, window=window)[0, 0]

        nodata = src.nodata
        if nodata is not None and value == nodata:
            return None

        # Guard against NaN nodata regardless of declared nodata value.
        if value != value:
            return None

        return float(value)
```