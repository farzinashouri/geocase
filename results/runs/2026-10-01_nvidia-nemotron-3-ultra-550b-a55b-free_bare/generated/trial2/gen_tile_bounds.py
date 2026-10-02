from pyproj import Transformer

# Web Mercator (EPSG:3857) world extent in meters
_WORLD_EXTENT = 20037508.342789244
_WORLD_SIZE = 2 * _WORLD_EXTENT

# Transformer from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
# always_xy=True ensures (x, y) -> (lon, lat) order
_TRANSFORMER = Transformer.from_crs("epsg:3857", "epsg:4326", always_xy=True)


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Return the geographic bounds (west, south, east, north) in WGS84 degrees
    for a Web Mercator tile (TMS scheme) at zoom level z, column x, row y.

    TMS scheme: origin at bottom-left, y increases northward.
    """
    if z < 0:
        raise ValueError("Zoom level must be non-negative")
    n_tiles = 1 << z  # 2**z
    if not (0 <= x < n_tiles and 0 <= y < n_tiles):
        raise ValueError("Tile coordinates out of range for zoom level")

    tile_size = _WORLD_SIZE / n_tiles

    # Tile bounds in Web Mercator meters (EPSG:3857)
    minx = -_WORLD_EXTENT + x * tile_size
    maxx = minx + tile_size
    miny = -_WORLD_EXTENT + y * tile_size
    maxy = miny + tile_size

    # Transform to WGS84 (EPSG:4326)
    west, south = _TRANSFORMER.transform(minx, miny)
    east, north = _TRANSFORMER.transform(maxx, maxy)

    return (west, south, east, north)