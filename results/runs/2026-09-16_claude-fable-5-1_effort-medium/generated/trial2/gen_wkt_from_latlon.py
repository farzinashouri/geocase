"""Build a WKT POINT from a WGS84 latitude/longitude pair.

WKT (and GIS tools generally) expect coordinates in X Y order, i.e.
longitude first, then latitude. User-facing APIs conventionally supply
(lat, lon), so this module swaps the order when serialising.
"""

import math


def wkt_from_latlon(lat, lon):
    """Return a WKT ``POINT`` string for a WGS84 latitude/longitude.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees, in [-90, 90].
    lon : float
        Longitude in decimal degrees, in [-180, 180].

    Returns
    -------
    str
        ``"POINT (lon lat)"`` with coordinates in WKT's X Y (lon lat) order.

    Raises
    ------
    TypeError
        If either value is not a real number (bools are rejected too).
    ValueError
        If either value is NaN/infinite or outside the WGS84 range.
    """
    lat = _to_finite_float(lat, "lat")
    lon = _to_finite_float(lon, "lon")

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat!r}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon!r}")

    # WKT is X Y, so longitude comes first.
    return f"POINT ({_fmt(lon)} {_fmt(lat)})"


def _to_finite_float(value, name):
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a number, got bool")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a number, got {type(value).__name__}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result


def _fmt(value):
    # repr() gives the shortest round-trip decimal representation and never
    # uses locale-specific separators; normalise -0.0 to 0.0 for tidiness.
    if value == 0.0:
        value = 0.0
    return repr(value)