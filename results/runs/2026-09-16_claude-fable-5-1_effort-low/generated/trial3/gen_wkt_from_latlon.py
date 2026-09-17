"""Build a WKT POINT from a WGS84 latitude/longitude pair.

WKT (and every GIS tool that reads it) expects coordinates in X Y order,
which for geographic coordinates means longitude first, then latitude.
Callers conventionally supply (lat, lon), so this module performs the swap.
"""

import math


def wkt_from_latlon(lat, lon):
    """Return a WKT ``POINT`` string for a WGS84 location.

    Args:
        lat: Latitude in decimal degrees, in [-90, 90].
        lon: Longitude in decimal degrees, in [-180, 180].

    Returns:
        A string of the form ``POINT (lon lat)``, i.e. X before Y as WKT requires.

    Raises:
        TypeError: if either value is not a real number (bools are rejected).
        ValueError: if either value is NaN/infinite or outside the WGS84 range.
    """
    lat = _to_float("lat", lat)
    lon = _to_float("lon", lon)

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be within [-90, 90], got {lat!r}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {lon!r}")

    return f"POINT ({_fmt(lon)} {_fmt(lat)})"


def _to_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise TypeError(f"{name} must be a real number, got {value!r}") from None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return value


def _fmt(value):
    # repr gives the shortest round-trippable representation; normalise -0.0
    # and drop a trailing ".0" so integers print cleanly (e.g. "POINT (10 20)").
    if value == 0.0:
        value = 0.0
    text = repr(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text