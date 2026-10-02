```python
import math

def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic bounds (west, south, east, north) in WGS84 degrees
    for a Web Mercator tile in the TMS tiling scheme.

    Parameters
    ----------
    z : int
        Zoom level.
    x : int
        Tile column (0 at west).
    y : int
        Tile row (0 at south).

    Returns
    -------
    tuple of float
        (west, south, east, north) in degrees.
    """
    n = 1 << z  # 2**z
    # Longitude bounds
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    # Latitude bounds using spherical Mercator formulas for TMS (y=0 at south)
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (n - y) / n))))
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (n - y - 1) / n))))
    return (west, south, east, north)
```