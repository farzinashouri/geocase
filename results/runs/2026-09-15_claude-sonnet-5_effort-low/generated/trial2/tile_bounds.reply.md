```python
import math


def tile_bounds(z, x, y):
    n = 2.0 ** z

    def lon(col):
        return col / n * 360.0 - 180.0

    def lat(row):
        rad = math.atan(math.sinh(math.pi * (1 - 2 * row / n)))
        return math.degrees(rad)

    west = lon(x)
    east = lon(x + 1)
    south = lat(y)
    north = lat(y + 1)

    return (west, south, east, north)
```