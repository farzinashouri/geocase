import math


def tile_bounds(z, x, y):
    n = 2 ** z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    def lat(row):
        angle = math.pi * (1 - 2 * row / n)
        return math.degrees(math.atan(math.sinh(angle)))

    south = lat(y)
    north = lat(y + 1)

    return (west, south, east, north)