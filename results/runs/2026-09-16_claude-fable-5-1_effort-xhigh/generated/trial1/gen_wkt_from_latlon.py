"""Build WKT ``POINT`` text from user-facing latitude/longitude input.

Users and most APIs supply coordinates as (latitude, longitude), but WKT is
written in x/y order: ``POINT (x y)``.  For a geographic CRS such as WGS84
(EPSG:4326) x is longitude and y is latitude, and that is the order shapely,
GEOS, GDAL/OGR, PostGIS, QGIS and rasterio expect when they parse WKT.
``wkt_from_latlon`` performs that swap so the returned string lands on the
right spot when loaded.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import SupportsFloat

__all__ = ["wkt_from_latlon"]


def _as_finite_float(value: SupportsFloat, name: str) -> float:
    """Coerce ``value`` to a finite float or raise a descriptive error."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {number!r}")
    return number


def _format_coordinate(number: float) -> str:
    """Render a float as a plain decimal WKT number token.

    ``repr`` gives the shortest string that round-trips to the same float, so
    no precision is lost and no spurious digits are added.  Formatting it via
    ``Decimal`` with ``'f'`` expands any exponent (``1e-05`` -> ``0.00001``),
    which keeps the token in the plain form every WKT reader accepts.  Adding
    ``0.0`` normalises ``-0.0`` to ``0.0``.
    """
    return format(Decimal(repr(number + 0.0)), "f")


def wkt_from_latlon(lat: SupportsFloat, lon: SupportsFloat) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as (lat, lon).

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, in the closed range [-90, 90].
    lon:
        Longitude in decimal degrees, in the closed range [-180, 180].

    Returns
    -------
    str
        ``"POINT (<lon> <lat>)"``.  Note the swap: WKT is x/y order, and for
        geographic coordinates x is longitude and y is latitude.

    Raises
    ------
    TypeError
        If either argument cannot be interpreted as a real number.
    ValueError
        If either argument is NaN, infinite, or outside its valid range.

    Examples
    --------
    >>> wkt_from_latlon(51.5074, -0.1278)    # London
    'POINT (-0.1278 51.5074)'
    >>> wkt_from_latlon(-33.8688, 151.2093)  # Sydney
    'POINT (151.2093 -33.8688)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0.0 0.0)'
    """
    latitude = _as_finite_float(lat, "lat")
    longitude = _as_finite_float(lon, "lon")

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"lat must be within [-90, 90], got {latitude!r}. "
            "If you passed (lon, lat), swap the arguments: this function "
            "takes (lat, lon)."
        )
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {longitude!r}")

    # WKT axis order is x then y, i.e. longitude then latitude.
    return f"POINT ({_format_coordinate(longitude)} {_format_coordinate(latitude)})"