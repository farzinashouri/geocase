"""WKT point construction from latitude/longitude coordinates.

WKT (and the GIS tools that read it) expect coordinates in X Y order,
which for WGS84 means longitude then latitude. User-facing APIs usually
hand over (lat, lon), so this module performs the swap explicitly.
"""

import math

__all__ = ["wkt_from_latlon"]


def wkt_from_latlon(lat, lon):
    """Return a WKT ``POINT`` for a WGS84 latitude/longitude pair.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees, in the range [-90, 90].
    lon : float
        Longitude in decimal degrees, in the range [-180, 180].

    Returns
    -------
    str
        A WKT string of the form ``POINT (lon lat)``. WKT is X Y ordered,
        so longitude is written first even though the function accepts
        latitude first.

    Raises
    ------
    TypeError
        If either coordinate is not a real number (booleans are rejected).
    ValueError
        If either coordinate is NaN or infinite, or out of WGS84 range.
    """
    lat = _to_finite_float(lat, "lat")
    lon = _to_finite_float(lon, "lon")

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be within [-90, 90], got {lat!r}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {lon!r}")

    # WKT is X Y, i.e. longitude before latitude.
    return f"POINT ({_fmt(lon)} {_fmt(lat)})"


def _to_finite_float(value, name):
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a number, got bool")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result


def _fmt(value):
    # repr gives the shortest round-tripping decimal form; avoid "-0.0".
    if value == 0.0:
        value = 0.0
    return repr(value)