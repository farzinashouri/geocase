import pyproj


def tile_bounds(z, x, y):
    transformer = pyproj.Transformer.from_epsg(3857, 4326, always_xy=True)
    
    extent = 20037508.34
    tile_size = 2 * extent / (2 ** z)
    
    west_m = -extent + x * tile_size
    east_m = west_m + tile_size
    south_m = -extent + y * tile_size
    north_m = south_m + tile_size
    
    west, south = transformer.transform(west_m, south_m)
    east, north = transformer.transform(east_m, north_m)
    
    return (west, south, east, north)