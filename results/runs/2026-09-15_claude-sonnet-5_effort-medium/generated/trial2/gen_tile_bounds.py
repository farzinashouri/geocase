import math


def tile_bounds(z, x, y):
    n = 2.0 ** z

    def lon(xt):
        return xt / n * 360.0 - 180.0

    def lat(yt):
        m = math.pi * (1 - 2 * yt / n)
        return math.degrees(math.atan(math.sinh(m)))

    west = lon(x)
    east = lon(x + 1)
    south = lat(y)
    north = lat(y + 1)

    return (west, south, east, north)