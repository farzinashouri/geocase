```python
"""Convert a WGS84 latitude/longitude pair into a WKT ``POINT`` string.

WKT (and every GIS tool that reads it) expects coordinates in ``X Y`` order,
which for geographic data means ``longitude latitude``. User-facing APIs
conventionally hand us ``(lat, lon)``, so this module's single job is to
validate the pair and emit it in the axis order WKT actually requires.
"""

from __future__ import annotations

import math
from numbers import Real

__all__ = ["wkt_from_latlon"]


def _as_finite_float(value: object, name: str) -> float:
    """Coerce ``value`` to a finite float or raise a descriptive error."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {number!r}")
    return number


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as ``(lat, lon)``.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, in the closed range ``[-90, 90]``.
    lon:
        Longitude in decimal degrees, in the closed range ``[-180, 180]``.

    Returns
    -------
    str
        ``"POINT (<lon> <lat>)"`` -- note the swap: WKT is ``X Y``, so the
        longitude comes first. Coordinates are rendered with ``repr`` so the
        full double precision round-trips through any WKT reader.

    Raises
    ------
    TypeError
        If either argument is not a real number (``bool`` is rejected too).
    ValueError
        If either argument is NaN/infinite or outside the WGS84 range.

    Examples
    --------
    >>> wkt_from_latlon(51.5074, -0.1278)   # London
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
            "If this value looks like a longitude, the arguments may be swapped: "
            "this function takes (lat, lon)."
        )
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {longitude!r}")

    # Normalise -0.0 to 0.0 so the output is canonical.
    latitude += 0.0
    longitude += 0.0

    # WKT axis order is X Y => longitude latitude.
    return f"POINT ({longitude!r} {latitude!r})"
```