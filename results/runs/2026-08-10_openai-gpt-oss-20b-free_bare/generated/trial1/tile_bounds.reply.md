```python
import math
from pyproj import Transformer

# Create a transformer from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326).
# always_xy=True ensures the input order is (x, y) = (lon, lat) in meters.
_transformer = Transformer.from_crs(3857, 4326, always_xy=True)

# World extent in Web Mercator meters.
_WM_EPSG_WORLD_MIN = -20037508.342789244
_WM_EPSG_WORLD_MAX =  20037508.342789244
_WM_EPSG_WORLD_SIZE = _WM_EPSG_WORLD_MAX - _WM_EPSG_WORLD_MIN  # 40075016.68557849


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic extent (west, south, east, north) in WGS84 degrees
    of a Web Mercator tile at zoom level `z` with column `x` and row `y`,
    using the TMS tiling scheme (origin at the bottom‑left).

    Parameters
    ----------
    z : int
        Zoom level (non‑negative integer).
    x : int
        Tile column index (0 ≤ x < 2**z).
    y : int
        Tile row index (0 ≤ y < 2**z).

    Returns
    -------
    tuple[float, float, float, float]
        (west, south, east, north) in degrees.

    Raises
    ------
    ValueError
        If `z` is negative or if `x` or `y` are outside the valid range.
    """
    if z < 0:
        raise ValueError("Zoom level z must be non‑negative")
    max_index = (1 << z) - 1
    if not (0 <= x <= max_index):
        raise ValueError(f"x must be in [0, {max_index}] for zoom level {z}")
    if not (0 <= y <= max_index):
        raise ValueError(f"y must be in [0, {max_index}] for zoom level {z}")

    # Size of one tile in Web Mercator meters.
    tile_size = _WM_EPSG_WORLD_SIZE / (1 << z)

    # Compute bounds in Web Mercator meters.
    west_m = _WM_EPSG_WORLD_MIN + x * tile_size
    east_m = west_m + tile_size
    south_m = _WM_EPSG_WORLD_MIN + y * tile_size
    north_m = south_m + tile_size

    # Transform to WGS84 degrees.
    west_lon, south_lat = _transformer.transform(west_m, south_m)
    east_lon, north_lat = _transformer.transform(east_m, north_m)

    return (west_lon, south_lat, east_lon, north_lat)
```