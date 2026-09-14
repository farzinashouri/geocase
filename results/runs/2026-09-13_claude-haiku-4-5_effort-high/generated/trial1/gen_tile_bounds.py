from pyproj import Transformer

_transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees of a Web Mercator tile (TMS scheme)."""
    MERC_MIN = -20037508.34
    MERC_MAX = 20037508.34
    
    tile_size = (MERC_MAX - MERC_MIN) / (2 ** z)
    
    west_merc = MERC_MIN + x * tile_size
    east_merc = MERC_MIN + (x + 1) * tile_size
    south_merc = MERC_MIN + y * tile_size
    north_merc = MERC_MIN + (y + 1) * tile_size
    
    west, south = _transformer.transform(west_merc, south_merc)
    east, north = _transformer.transform(east_merc, north_merc)
    
    return (west, south, east, north)