```python
import math


def tile_bounds(z, x, y):
    """Return (west, south, east, north) WGS84 bounds for a TMS tile."""
    n = 2 ** z
    y_xyz = n - 1 - y

    def lat(row):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * row / n))))

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = lat(y_xyz)
    south = lat(y_xyz + 1)

    return (float(west), float(south), float(east), float(north))
```