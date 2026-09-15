Key detail: WKT is `POINT (X Y)`, so the longitude goes first — the function swaps the user-facing `(lat, lon)` order on output. I wasn't able to execute a verification run here (the sandbox declined the write/run), so this is delivered unrun.

```python
"""Build WKT ``POINT`` strings from WGS84 latitude/longitude pairs.

WKT carries no axis metadata: a ``POINT`` is written ``X Y``, and GIS tools
reading WGS84 geometry take that as ``longitude latitude``.  The public
argument order here is the user-facing ``(lat, lon)`` convention, so the two
values are swapped on the way out.  That swap is the whole job of this module --
emitting ``POINT (lat lon)`` is the classic way to land a feature in the wrong
hemisphere.
"""

from __future__ import annotations

import math
from decimal import Decimal

__all__ = ["wkt_from_latlon"]

_LAT_LIMIT = 90.0
_LON_LIMIT = 180.0


def _coerce(value: object, name: str, limit: float) -> float:
    """Return ``value`` as a finite float inside ``[-limit, limit]``."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if not -limit <= number <= limit:
        raise ValueError(f"{name} must be in [-{limit:g}, {limit:g}], got {number!r}")
    return number


def _format(value: float) -> str:
    """Render ``value`` as plain fixed-point text that round-trips to itself.

    ``repr`` gives the shortest string that parses back to the same float, but
    it may use exponent notation (``1e-07``) for small magnitudes, which not
    every WKT reader accepts.  Routing through ``Decimal`` keeps the digits of
    that shortest form while forcing fixed-point output.
    """
    if value == 0.0:  # collapse -0.0, a valid float but a wart in WKT output
        return "0"
    return format(Decimal(repr(value)), "f")


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return the WKT ``POINT`` for a WGS84 position given as latitude, longitude.

    Args:
        lat: Latitude in decimal degrees, ``-90`` to ``90``.
        lon: Longitude in decimal degrees, ``-180`` to ``180``.

    Returns:
        A WKT point such as ``'POINT (-122.4194 37.7749)'`` -- longitude first,
        matching the ``X Y`` order shapely, PostGIS, GDAL and QGIS expect.

    Raises:
        TypeError: If an argument is not a real number.
        ValueError: If an argument is NaN, infinite, or out of range.
    """
    latitude = _coerce(lat, "lat", _LAT_LIMIT)
    longitude = _coerce(lon, "lon", _LON_LIMIT)
    return f"POINT ({_format(longitude)} {_format(latitude)})"
```