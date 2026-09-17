Writing the module now.

```python
"""WKT point construction from WGS84 latitude/longitude.

WKT (and GIS tools in general) order coordinates as X Y, i.e. longitude
first, then latitude. User-facing APIs conventionally supply (lat, lon),
so this module swaps the order when building the POINT string.
"""

from __future__ import annotations

import math


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as (lat, lon).

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, in [-90, 90].
    lon:
        Longitude in decimal degrees, in [-180, 180].

    Returns
    -------
    str
        A WKT string of the form ``POINT (lon lat)`` — longitude (X) first,
        latitude (Y) second, as required by the WKT specification.

    Raises
    ------
    TypeError
        If either coordinate is not a real number.
    ValueError
        If either coordinate is NaN/infinite or outside its valid range.
    """
    lat_f = _to_finite_float(lat, "lat")
    lon_f = _to_finite_float(lon, "lon")

    if not -90.0 <= lat_f <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat_f!r}")
    if not -180.0 <= lon_f <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon_f!r}")

    # X = longitude, Y = latitude. repr() gives a shortest round-trip
    # representation, so no precision is lost and no trailing noise appears.
    return f"POINT ({lon_f!r} {lat_f!r})"


def _to_finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result
```