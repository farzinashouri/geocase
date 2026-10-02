import math
from pyproj import Transformer

# Web Mercator radius (semi-major axis of WGS84 used in Web Mercator)
_R = 6378137.0
_HALF_WORLD = math.pi * _R  # 20037508.342789244 meters

# Transformer from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
# always_xy=True ensures (x, y) order for both source and target CRS.
_TRANSFORMER = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic bounds (west, south, east, north) in WGS84 degrees
    for a Web Mercator tile (TMS scheme) at zoom level `z`, column `x`, row `y`.

    Parameters
    ----------
    z : int
        Zoom level (non-negative).
    x : int
        Tile column (0 <= x < 2^z).
    y : int
        Tile row (0 <= y < 2^z), increasing northward.

    Returns
    -------
    tuple[float, float, float, float]
        (west, south, east, north) in decimal degrees.
    """
    if z < 0:
        raise ValueError("Zoom level must be non-negative")
    n = 1 << z  # 2^z
    if not (0 <= x < n and 0 <= y < n):
        raise ValueError("Tile coordinates out of range for zoom level")

    tile_size = (2 * _HALF_WORLD) / n  # meters per tile at this zoom

    # Tile bounds in Web Mercator (EPSG:3857) meters
    west = x * tile_size - _HALF_WORLD
    east = (x + 1) * tile_size - _HALF_WORLD
    south = y * tile_size - _HALF_WORLD
    north = (y + 1) * tile_size - _HALF_WORLD

    # Convert to WGS84 (longitude, latitude)
    west_lon, south_lat = _TRANSFORMER.transform(west, south)
    east_lon, north_lat = _TRANSFORMER.transform(east, north)

    return (west_lon, south_lat, east_lon, north_lat)