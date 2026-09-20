```python
"""Build a WKT POINT from a (latitude, longitude) pair.

WGS84 coordinates are conventionally supplied to user-facing APIs as
(lat, lon), but WKT -- like GeoJSON and most GIS tooling -- is axis-ordered
as (x y), i.e. (longitude latitude). This module performs that swap so the
resulting geometry loads at the intended location in standard GIS tools.
"""

from __future__ import annotations

import math
from numbers import Real

__all__ = ["wkt_from_latlon"]


def _as_finite_float(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result


def wkt_from_latlon(lat, lon) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as (latitude, longitude).

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, in the closed range [-90, 90].
    lon:
        Longitude in decimal degrees, in the closed range [-180, 180].

    Returns
    -------
    str
        A WKT string of the form ``POINT (<lon> <lat>)``. WKT stores
        coordinates as ``x y``, so longitude is written first.

    Raises
    ------
    TypeError
        If either argument is not a real number.
    ValueError
        If either argument is NaN/infinite or outside the valid WGS84 range.

    Examples
    --------
    >>> wkt_from_latlon(51.5074, -0.1278)
    'POINT (-0.1278 51.5074)'
    """
    lat_f = _as_finite_float(lat, "lat")
    lon_f = _as_finite_float(lon, "lon")

    if not -90.0 <= lat_f <= 90.0:
        raise ValueError(f"lat must be within [-90, 90], got {lat_f!r}")
    if not -180.0 <= lon_f <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {lon_f!r}")

    # repr() gives the shortest round-tripping decimal, so no precision is lost.
    return f"POINT ({lon_f!r} {lat_f!r})"
```