import math

def tile_bounds(z, x, y):
    # Web Mercator extent in meters
    EARTH_RADIUS = 6378137
    EXTENT = math.pi * EARTH_RADIUS
    
    # Number of tiles at this zoom level
    n = 2 ** z
    
    # Convert TMS y to standard tile coordinate system
    y_std = n - 1 - y
    
    # Size of each tile in Web Mercator meters
    tile_size = 2 * EXTENT / n
    
    # Bounds in Web Mercator
    west_m = -EXTENT + x * tile_size
    east_m = west_m + tile_size
    north_m = EXTENT - y_std * tile_size
    south_m = north_m - tile_size
    
    # Convert Web Mercator to WGS84
    def web_mercator_to_wgs84(x_m, y_m):
        lon = x_m / EARTH_RADIUS
        lat = 2 * math.atan(math.exp(y_m / EARTH_RADIUS)) - math.pi / 2
        return math.degrees(lon), math.degrees(lat)
    
    lon_west, lat_north = web_mercator_to_wgs84(west_m, north_m)
    lon_east, lat_south = web_mercator_to_wgs84(east_m, south_m)
    
    return (lon_west, lat_south, lon_east, lat_north)