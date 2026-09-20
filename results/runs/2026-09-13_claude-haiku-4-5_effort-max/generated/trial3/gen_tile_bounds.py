from pyproj import Transformer

def tile_bounds(z, x, y):
    max_extent = 20037508.34
    tile_size = (2 * max_extent) / (2 ** z)
    
    west_proj = -max_extent + x * tile_size
    east_proj = west_proj + tile_size
    south_proj = -max_extent + y * tile_size
    north_proj = south_proj + tile_size
    
    transformer = Transformer.from_epsg(3857, 4326)
    west, south = transformer.transform(west_proj, south_proj)
    east, north = transformer.transform(east_proj, north_proj)
    
    return (west, south, east, north)