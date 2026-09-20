import math

def tile_bounds(z, x, y):
    """Get the geographic extent of a Web Mercator tile in WGS84 degrees."""
    EARTH_RADIUS = 6378137.0
    
    def merc_to_wgs84(merc_x, merc_y):
        lon = (merc_x / EARTH_RADIUS) * (180.0 / math.pi)
        lat = (2 * math.atan(math.exp(merc_y / EARTH_RADIUS)) - math.pi / 2) * (180.0 / math.pi)
        return lon, lat
    
    MAX_EXTENT = EARTH_RADIUS * math.pi
    n_tiles = 2 ** z
    tile_size = 2 * MAX_EXTENT / n_tiles
    
    merc_west = -MAX_EXTENT + x * tile_size
    merc_east = merc_west + tile_size
    merc_north = MAX_EXTENT - y * tile_size
    merc_south = merc_north - tile_size
    
    west, south = merc_to_wgs84(merc_west, merc_south)
    east, north = merc_to_wgs84(merc_east, merc_north)
    
    return (west, south, east, north)