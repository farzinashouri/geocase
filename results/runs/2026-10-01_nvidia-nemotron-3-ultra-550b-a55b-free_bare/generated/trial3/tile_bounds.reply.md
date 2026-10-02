```python
import math

def tile_bounds(z, x, y):
    """
    Return the geographic bounds (west, south, east, north) in WGS84 degrees
    for a Web Mercator tile (z, x, y) in TMS tiling scheme.

    Parameters
    ----------
    z : int
        Zoom level.
    x : int
        Tile column (0 at left, increasing eastward).
    y : int
        Tile row (0 at bottom, increasing northward) per TMS convention.

    Returns
    -------
    tuple of float
        (west, south, east, north) in degrees (EPSG:4326).
    """
    # Web Mercator uses a spherical Earth with radius 6378137 meters
    R = 6378137.0
    world_width = 2 * math.pi * R
    n = 1 << z  # 2 ** z
    tile_width = world_width / n
    origin = -world_width / 2.0

    west_m = origin + x * tile_width
    south_m = origin + y * tile_width
    east_m = west_m + tile_width
    north_m = south_m + tile_width

    def _mercator_to_lonlat(mx, my):
        lon = mx / R * 180.0 / math.pi
        lat = math.atan(math.sinh(my / R)) * 180.0 / math.pi
        return lon, lat

    west, south = _mercator_to_lonlat(west_m, south_m)
    east, north = _mercator_to_lonlat(east_m, north_m)

    return (west, south, east, north)
```