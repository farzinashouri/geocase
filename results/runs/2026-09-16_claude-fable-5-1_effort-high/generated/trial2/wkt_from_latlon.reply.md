```python
"""Build a WKT POINT from a WGS84 latitude/longitude pair.

WKT (and GIS tools generally) expect coordinates as ``X Y`` = ``lon lat``,
whereas user-facing APIs conventionally supply ``lat, lon``. This module
performs that swap and validates the inputs so the result loads correctly
in standard GIS tools.
"""

from __future__ import annotations

import math
from numbers import Real

__all__ = ["wkt_from_latlon"]


def _to_float(value: object, name: str) -> float:
    """Coerce a numeric-like value to float, rejecting bools, NaN and inf."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    result = float(value)
    if math.isnan(result) or math.isinf(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as ``(lat, lon)``.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, in the range [-90, 90].
    lon:
        Longitude in decimal degrees, in the range [-180, 180].

    Returns
    -------
    str
        A WKT string of the form ``POINT (lon lat)``. Note the axis order:
        WKT uses X then Y, i.e. longitude first, latitude second.

    Raises
    ------
    TypeError
        If either argument is not a real number.
    ValueError
        If either argument is NaN/infinite or outside its valid range.

    Examples
    --------
    >>> wkt_from_latlon(51.5074, -0.1278)
    'POINT (-0.1278 51.5074)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0 0)'
    """
    lat_f = _to_float(lat, "lat")
    lon_f = _to_float(lon, "lon")

    if not -90.0 <= lat_f <= 90.0:
        raise ValueError(f"lat must be within [-90, 90], got {lat_f!r}")
    if not -180.0 <= lon_f <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {lon_f!r}")

    # Normalise -0.0 to 0.0 so the output is canonical.
    lat_f += 0.0
    lon_f += 0.0

    # repr() gives the shortest round-trippable decimal for floats and never
    # produces locale-specific separators or scientific notation for values
    # in these ranges (|x| <= 180, and Python only switches to exponent form
    # below 1e-4, which we guard against below).
    return f"POINT ({_fmt(lon_f)} {_fmt(lat_f)})"


def _fmt(value: float) -> str:
    """Format a coordinate as plain decimal text with no exponent."""
    if value == math.floor(value) and abs(value) < 1e16:
        return str(int(value))
    text = repr(value)
    if "e" in text or "E" in text:
        # Fall back to fixed notation for very small magnitudes (e.g. 1e-05).
        text = format(value, ".17f").rstrip("0").rstrip(".")
    return text
```