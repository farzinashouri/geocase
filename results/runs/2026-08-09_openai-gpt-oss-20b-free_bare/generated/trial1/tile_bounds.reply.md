```python
import math

# Constants for Web Mercator
EARTH_RADIUS = 6378137.0  # in meters
PI = math.pi
RADIUS_OVER_PI = EARTH_RADIUS / PI
PI_OVER_R = PI / EARTH_RADIUS

def _meters_to_lon(x_m: float) -> float:
    """Convert Web Mercator X coordinate (meters) to longitude (degrees)."""
    return x_m * RADIUS_OVER_PI

def _meters_to_lat(y_m: float) -> float:
    """Convert Web Mercator Y coordinate (meters) to latitude (degrees)."""
    # Inverse of Mercator projection
    return math.degrees(2 * math.atan(math.exp(y_m * PI_OVER_R)) - PI / 2)

def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic extent (west, south, east, north) in WGS84 degrees
    of the Web Mercator tile at zoom level `z` with column `x` and row `y`
    using the TMS tiling scheme.

    Parameters
    ----------
    z : int
        Zoom level (non-negative integer).
    x : int
        Tile column (0 <= x < 2**z).
    y : int
        Tile row (0 <= y < 2**z), with y=0 at the bottom (south).

    Returns
    -------
    tuple[float, float, float, float]
        (west, south, east, north) in degrees.
    """
    if z < 0:
        raise ValueError("Zoom level must be non-negative")
    max_index = 1 << z
    if not (0 <= x < max_index) or not (0 <= y < max_index):
        raise ValueError(f"Tile coordinates out of bounds for zoom {z}")

    # Size of one tile in meters
    tile_size = 2 * PI * EARTH_RADIUS / max_index

    # West and east bounds in meters
    west_m = -PI * EARTH_RADIUS + x * tile_size
    east_m = west_m + tile_size

    # South and north bounds in meters (TMS origin at bottom)
    south_m = -PI * EARTH_RADIUS + y * tile_size
    north_m = south_m + tile_size

    # Convert to geographic coordinates
    west = _meters_to_lon(west_m)
    east = _meters_to_lon(east_m)
    south = _meters_to_lat(south_m)
    north = _meters_to_lat(north_m)

    return (west, south, east, north)
```