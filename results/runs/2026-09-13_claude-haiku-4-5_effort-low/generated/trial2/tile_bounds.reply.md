```python
import math

def tile_bounds(z, x, y):
    """
    Get the WGS84 geographic extent of a Web Mercator tile in TMS scheme.
    
    Args:
        z: Zoom level
        x: Tile column (0 to 2^z - 1)
        y: Tile row (0 to 2^z - 1, bottom-up in TMS)
    
    Returns:
        Tuple of (west, south, east, north) in WGS84 degrees
    """
    EARTH_RADIUS = 6378137.0
    MERC_MAX = math.pi * EARTH_RADIUS
    
    tile_size = (2 * MERC_MAX) / (2 ** z)
    
    merc_west = -MERC_MAX + x * tile_size
    merc_east = merc_west + tile_size
    merc_south = -MERC_MAX + y * tile_size
    merc_north = merc_south + tile_size
    
    def merc_to_wgs84(mx, my):
        lon = mx / MERC_MAX * 180
        lat = math.degrees(2 * math.atan(math.exp(my / EARTH_RADIUS)) - math.pi / 2)
        return lon, lat
    
    lon_west, lat_south = merc_to_wgs84(merc_west, merc_south)
    lon_east, lat_north = merc_to_wgs84(merc_east, merc_north)
    
    return (lon_west, lat_south, lon_east, lat_north)
```