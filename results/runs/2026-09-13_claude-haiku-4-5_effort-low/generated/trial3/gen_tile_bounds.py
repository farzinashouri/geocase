from pyproj import Transformer

_transformer = Transformer.from_epsg(3857, 4326, always_xy=True)

def tile_bounds(z, x, y):
    EARTH_RADIUS = 20037508.34
    n = 2 ** z
    extent = 2 * EARTH_RADIUS
    
    west_merc = -EARTH_RADIUS + (x / n) * extent
    east_merc = -EARTH_RADIUS + ((x + 1) / n) * extent
    south_merc = -EARTH_RADIUS + (y / n) * extent
    north_merc = -EARTH_RADIUS + ((y + 1) / n) * extent
    
    west, south = _transformer.transform(west_merc, south_merc)
    east, north = _transformer.transform(east_merc, north_merc)
    
    return (float(west), float(south), float(east), float(north))