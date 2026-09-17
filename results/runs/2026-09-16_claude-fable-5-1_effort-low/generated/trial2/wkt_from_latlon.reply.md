```python
"""Build a WKT POINT string from a WGS84 latitude/longitude pair.

WKT (and GIS tools generally) expect coordinates in X Y order, i.e.
``POINT(lon lat)``. User-facing APIs conventionally supply ``(lat, lon)``,
so this module swaps the order on the way out.
"""

import math


def wkt_from_latlon(lat, lon):
    """Return a WKT ``POINT`` for a WGS84 location given as (lat, lon).

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees, -90..90.
    lon : float
        Longitude in decimal degrees, -180..180.

    Returns
    -------
    str
        ``"POINT (<lon> <lat>)"`` with X (longitude) first, as WKT requires.

    Raises
    ------
    TypeError
        If either value is not a real number (bools are rejected too).
    ValueError
        If either value is NaN/infinite or outside the valid WGS84 range.
    """
    lat_f = _to_float("lat", lat)
    lon_f = _to_float("lon", lon)

    if not -90.0 <= lat_f <= 90.0:
        raise ValueError(f"lat must be within [-90, 90], got {lat_f!r}")
    if not -180.0 <= lon_f <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {lon_f!r}")

    # WKT axis order is X Y => longitude then latitude.
    return f"POINT ({_fmt(lon_f)} {_fmt(lat_f)})"


def _to_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return value


def _fmt(value):
    # repr() gives the shortest round-tripping representation; normalise
    # negative zero so output is stable.
    if value == 0.0:
        value = 0.0
    return repr(value)
```