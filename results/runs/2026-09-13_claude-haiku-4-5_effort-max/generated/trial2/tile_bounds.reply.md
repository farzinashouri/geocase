```python
from pyproj import Transformer, CRS

def tile_bounds(z, x, y):
    y = (2 ** z) - 1 - y
    
    transformer = Transformer.from_crs(
        CRS.from_epsg(3857), 
        CRS.from_epsg(4326), 
        always_xy=True
    )
    
    n = 2 ** z
    extent = 20037508.34
    tile_size = 2 * extent / n
    
    west_m = -extent + x * tile_size
    east_m = -extent + (x + 1) * tile_size
    south_m = extent - (y + 1) * tile_size
    north_m = extent - y * tile_size
    
    west, south = transformer.transform(west_m, south_m)
    east, north = transformer.transform(east_m, north_m)
    
    return (west, south, east, north)
```