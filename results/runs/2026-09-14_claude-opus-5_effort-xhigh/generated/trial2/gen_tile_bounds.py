"""Web Mercator (TMS) tile geometry.

Converts a TMS tile address into its geographic extent on the WGS84
datum (EPSG:4326), for tiles cut from the spherical Web Mercator
projection (EPSG:3857) used by standard web map tile pyramids.

TMS (Tile Map Service) numbers rows from the *bottom* of the pyramid:
row ``y = 0`` is the southernmost row, and row ``y = 2**z - 1`` is the
northernmost. This is the vertical mirror of the XYZ / "slippy map"
scheme, where row 0 is the northernmost.
"""

import math

__all__ = ["tile_bounds"]


def tile_bounds(z, x, y):
    """Return the WGS84 extent of a TMS Web Mercator tile.

    Parameters
    ----------
    z : int
        Zoom level (>= 0). The pyramid at zoom ``z`` is ``2**z`` tiles wide
        and ``2**z`` tiles tall.
    x : int
        Tile column, increasing eastward from 0 at the antimeridian.
    y : int
        Tile row in the TMS convention, increasing *northward* from 0 at the
        southern edge of the Web Mercator extent.

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` in decimal degrees. Longitudes span
        [-180, 180]; latitudes span the Web Mercator clip limits of
        approximately [-85.0511, 85.0511].

    Raises
    ------
    ValueError
        If ``z`` is negative, or if ``x`` or ``y`` falls outside
        ``[0, 2**z - 1]``.

    Examples
    --------
    >>> tile_bounds(0, 0, 0)  # doctest: +ELLIPSIS
    (-180.0, -85.05112877980659, 180.0, 85.05112877980659)
    >>> tile_bounds(1, 0, 0)  # south-west quadrant  # doctest: +ELLIPSIS
    (-180.0, -85.05112877980659, 0.0, 0.0)
    """
    z = _as_index(z, "z")
    x = _as_index(x, "x")
    y = _as_index(y, "y")

    if z < 0:
        raise ValueError("zoom must be non-negative, got {!r}".format(z))

    n = 1 << z  # tiles per axis at this zoom
    if not 0 <= x < n:
        raise ValueError(
            "x must be in [0, {}] at zoom {}, got {!r}".format(n - 1, z, x)
        )
    if not 0 <= y < n:
        raise ValueError(
            "y must be in [0, {}] at zoom {}, got {!r}".format(n - 1, z, y)
        )

    # Longitude is linear in the projected x axis.
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # Latitude is the inverse Mercator of the projected y axis. Because TMS
    # rows grow northward, row y covers the fraction [y/n, (y+1)/n] of the
    # projected extent measured up from the southern edge.
    south = _lat_from_fraction(y / n)
    north = _lat_from_fraction((y + 1) / n)

    return (float(west), float(south), float(east), float(north))


def _lat_from_fraction(t):
    """Inverse spherical Mercator for a height fraction measured from the south.

    ``t = 0`` maps to the southern clip limit, ``t = 1`` to the northern one.
    """
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * t - 1.0))))


def _as_index(value, name):
    """Coerce a tile index to ``int``, rejecting non-integral values."""
    index = int(value)
    if index != value:
        raise ValueError("{} must be an integer, got {!r}".format(name, value))
    return index