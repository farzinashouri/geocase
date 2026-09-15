"""Build WKT ``POINT`` geometries from WGS84 latitude/longitude pairs.

Importing this module has no side effects.

Axis order is the subtle part. Callers quote coordinates as (lat, lon) --
that is the convention for user-facing APIs, GPS readouts and street
addresses -- but WKT is an X/Y format, and for a geographic CRS such as
WGS84 (EPSG:4326) X is longitude and Y is latitude. So the emitted text is
``POINT (lon lat)``. Writing the arguments in the order they arrive would
produce a syntactically valid geometry that silently lands somewhere else
on the globe (Zurich, 47.37 N 8.54 E, would plot in the Arabian Sea), which
is exactly the kind of error that survives all the way into a map.

Only the standard library is used: the transformation is a reordering and a
number-to-string conversion, not a reprojection, so shapely/pyproj would add
dependencies without adding correctness.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

_MAX_ABS_LAT = 90.0
_MAX_ABS_LON = 180.0

# 9 decimal places is ~0.1 mm at the equator, far finer than any WGS84 fix,
# so the round trip through text loses nothing that was ever measured.
_DECIMALS = 9


def _as_finite_float(value, name):
    """Coerce ``value`` to a finite float or raise with a useful message."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _format_ordinate(value):
    """Render a coordinate in plain decimal notation.

    ``repr`` would be shorter but emits exponents for small magnitudes
    (``1e-07``), and a number of WKT readers -- including some database and
    desktop GIS parsers -- reject scientific notation. Fixed notation with
    trailing zeros trimmed keeps the output both exact and portable.
    """
    text = f"{value:.{_DECIMALS}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):  # negative zero and underflow both mean the origin
        text = "0"
    return text


def wkt_from_latlon(lat, lon):
    """Return the WKT ``POINT`` for a WGS84 latitude/longitude pair.

    Args:
        lat: Latitude in decimal degrees, -90 to 90 inclusive.
        lon: Longitude in decimal degrees, -180 to 180 inclusive.

    Returns:
        A ``POINT (x y)`` string in longitude-latitude (X Y) order, ready for
        any OGC-conformant reader.

    Raises:
        TypeError: If either argument is not a real number.
        ValueError: If either argument is non-finite or out of range.

    >>> wkt_from_latlon(47.3769, 8.5417)
    'POINT (8.5417 47.3769)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0 0)'
    >>> wkt_from_latlon(-33.8688, 151.2093)
    'POINT (151.2093 -33.8688)'
    """
    latitude = _as_finite_float(lat, "lat")
    longitude = _as_finite_float(lon, "lon")

    if abs(latitude) > _MAX_ABS_LAT:
        raise ValueError(
            f"lat must be between -{_MAX_ABS_LAT} and {_MAX_ABS_LAT} degrees, "
            f"got {latitude!r}; arguments are (lat, lon), not (lon, lat)"
        )
    if abs(longitude) > _MAX_ABS_LON:
        raise ValueError(
            f"lon must be between -{_MAX_ABS_LON} and {_MAX_ABS_LON} degrees, "
            f"got {longitude!r}"
        )

    # X first, then Y: longitude precedes latitude in the output.
    return f"POINT ({_format_ordinate(longitude)} {_format_ordinate(latitude)})"