"""Geographic bounds of Web Mercator tiles addressed with the TMS scheme.

TMS tile addressing: at zoom ``z`` the world is a ``2**z`` by ``2**z`` grid of
tiles in the Web Mercator (EPSG:3857) square. Column ``x`` increases eastward
from the western edge; row ``y`` increases *northward* from the southern edge
(the opposite of the XYZ/"slippy map" scheme, where row 0 is at the top).
"""

import math

__all__ = ["tile_bounds"]

# Half the side length of the Web Mercator square, in meters
# (equatorial radius of the WGS84 spheroid times pi).
_ORIGIN_SHIFT = 6378137.0 * math.pi


def _merc_x_to_lon(mx):
    """Convert a Web Mercator x coordinate (meters) to longitude (degrees)."""
    return math.degrees(mx / 6378137.0)


def _merc_y_to_lat(my):
    """Convert a Web Mercator y coordinate (meters) to latitude (degrees)."""
    return math.degrees(2.0 * math.atan(math.exp(my / 6378137.0)) - math.pi / 2.0)


def tile_bounds(z, x, y):
    """Return the WGS84 extent of the TMS tile ``(z, x, y)``.

    Parameters
    ----------
    z : int
        Zoom level (non-negative).
    x : int
        Tile column, ``0 <= x < 2**z``, increasing eastward.
    y : int
        Tile row in the TMS scheme, ``0 <= y < 2**z``, increasing northward
        (row 0 touches the southern edge of the Web Mercator square).

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` in WGS84 degrees.
    """
    n = 2 ** z
    if not (0 <= x < n) or not (0 <= y < n):
        raise ValueError(
            "tile indices out of range for zoom %r: x=%r, y=%r" % (z, x, y)
        )

    tile_size = 2.0 * _ORIGIN_SHIFT / n  # tile side length in meters

    west_m = -_ORIGIN_SHIFT + x * tile_size
    east_m = -_ORIGIN_SHIFT + (x + 1) * tile_size
    south_m = -_ORIGIN_SHIFT + y * tile_size
    north_m = -_ORIGIN_SHIFT + (y + 1) * tile_size

    return (
        _merc_x_to_lon(west_m),
        _merc_y_to_lat(south_m),
        _merc_x_to_lon(east_m),
        _merc_y_to_lat(north_m),
    )
