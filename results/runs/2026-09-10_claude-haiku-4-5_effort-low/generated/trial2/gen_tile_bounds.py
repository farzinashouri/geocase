import math
import pyproj

_transformer = pyproj.Transformer.from_epsg(3857, 4326)


def tile_bounds(z, x, y):
    EARTH_RADIUS = 6378137
    EXTENT = EARTH_RADIUS * math.pi
    
    tile_size = (2 * EXTENT) / (2 ** z)
    
    west_m = -EXTENT + x * tile_size
    east_m = -EXTENT + (x + 1) * tile_size
    south_m = -EXTENT + y * tile_size
    north_m = -EXTENT + (y + 1) * tile_size
    
    west, south = _transformer.transform(west_m, south_m)
    east, north = _transformer.transform(east_m, north_m)
    
    return (west, south, east, north)