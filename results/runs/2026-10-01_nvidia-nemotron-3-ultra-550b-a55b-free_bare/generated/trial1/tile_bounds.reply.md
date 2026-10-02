```python
import math

def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic bounds (west, south, east, north) in WGS84 degrees
    for a Web Mercator tile using the TMS tiling scheme.

    Parameters
    ----------
    z : int
        Zoom level.
    x : int
        Tile column (0 at left, increasing eastward).
    y : int
        Tile row (0 at bottom, increasing northward).

    Returns
    -------
    tuple[float, float, float, float]
        (west, south, east, north) in decimal degrees.
    """
    n = 2 ** z

    # Longitude bounds are linear
    west = x * 360.0 / n - 180.0
    east = (x + 1) * 360.0 / n - 180.0

    # Latitude bounds via spherical Web Mercator (EPSG:3857)
    R = 6378137.0  # Earth radius in meters for Web Mercator
    world_height = 2 * math.pi * R
    tile_height = world_height / n

    # TMS origin (0,0) is at the south-west corner of the world extent
    y_min_m = -math.pi * R + y * tile_height
    y_max_m = -math.pi * R + (y + 1) * tile_height

    south = math.degrees(math.atan(math.sinh(y_min_m / R)))
    north = math.degrees(math.atan(math.sinh(y_max_m / R)))

    return (west, south, east, north)
```