def tile_bounds(z, x, y):
    import math
    
    EARTH_RADIUS = 20037508.34
    n = 2 ** z
    tile_size = (2 * EARTH_RADIUS) / n
    
    west_merc = -EARTH_RADIUS + x * tile_size
    east_merc = west_merc + tile_size
    north_merc = EARTH_RADIUS - y * tile_size
    south_merc = north_merc - tile_size
    
    west = west_merc * 180 / EARTH_RADIUS
    east = east_merc * 180 / EARTH_RADIUS
    south = math.degrees(2 * math.atan(math.exp(south_merc / EARTH_RADIUS)) - math.pi / 2)
    north = math.degrees(2 * math.atan(math.exp(north_merc / EARTH_RADIUS)) - math.pi / 2)
    
    return (west, south, east, north)