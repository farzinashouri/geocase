import math

# Web Mercator projection constants (EPSG:3857)
_EARTH_RADIUS = 6378137.0  # meters
_MAX_MERC = math.pi * _EARTH_RADIUS  # ~20037508.342789244 meters


def _mercator_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (EPSG:3857) coordinates to WGS84 (EPSG:4326) longitude/latitude."""
    lon = x / _MAX_MERC * 180.0
    lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / _MAX_MERC)) - math.pi / 2.0)
    return lon, lat


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic extent (west, south, east, north) in WGS84 degrees
    of a Web Mercator map tile using the TMS tiling scheme.

    Parameters
    ----------
    z : int
        Zoom level (0 = whole world).
    x : int
        Tile column (0 at left/west).
    y : int
        Tile row (0 at bottom/south, TMS origin).

    Returns
    -------
    tuple of float
        (west, south, east, north) in decimal degrees.
    """
    if z < 0:
        raise ValueError("Zoom level must be non-negative")
    n_tiles = 1 << z  # 2**z
    tile_size = 2.0 * _MAX_MERC / n_tiles

    # TMS origin is bottom-left (south-west)
    x_min = -_MAX_MERC + x * tile_size
    x_max = x_min + tile_size
    y_min = -_MAX_MERC + y * tile_size
    y_max = y_min + tile_size

    west, south = _mercator_to_lonlat(x_min, y_min)
    east, north = _mercator_to_lonlat(x_max, y_max)

    return (west, south, east, north)