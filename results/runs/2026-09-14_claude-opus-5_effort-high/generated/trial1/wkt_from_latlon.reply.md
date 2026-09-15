```python
"""Build WKT ``POINT`` geometries from WGS84 latitude/longitude pairs.

The one thing worth being explicit about: WKT — like essentially every
GIS format that stores plain coordinate pairs — is written in ``x y``
order.  For geographic coordinates that means ``POINT (lon lat)``, not
``POINT (lat lon)``.  Human-facing APIs conventionally hand out
``(lat, lon)``, so this module takes that order and does the swap in one
place, which is the only place a caller should have to think about it.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon", "MAX_LATITUDE", "MAX_LONGITUDE"]

MAX_LATITUDE = 90.0
MAX_LONGITUDE = 180.0

# Enough decimal places to round-trip a float64 degree value exactly;
# 1e-9 degrees is already well under a millimetre on the ground.
_MAX_DECIMALS = 17


def _to_float(value: object, name: str) -> float:
    """Coerce *value* to a finite float or raise ``ValueError``/``TypeError``."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number, not bool")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _format_ordinate(value: float) -> str:
    """Render *value* as a decimal WKT number.

    ``repr`` gives the shortest round-tripping representation, but it
    switches to exponent notation for small magnitudes (``1e-07``), which
    parts of the WKT ecosystem reject.  Fall back to fixed notation in
    that case and trim the padding.
    """
    text = repr(value)
    if "e" not in text and "E" not in text:
        return text

    text = f"{value:.{_MAX_DECIMALS}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0.0"


def wkt_from_latlon(lat, lon) -> str:
    """Return the WKT ``POINT`` for a WGS84 position given as (lat, lon).

    Args:
        lat: Latitude in decimal degrees, within [-90, 90].
        lon: Longitude in decimal degrees, within [-180, 180].

    Returns:
        A WKT string such as ``'POINT (-122.4194 37.7749)'``, with the
        ordinates in the ``x y`` (longitude, latitude) order that GIS
        tools expect.

    Raises:
        TypeError: If an argument is not a real number.
        ValueError: If an argument is non-finite or out of range.

    Example:
        >>> wkt_from_latlon(37.7749, -122.4194)
        'POINT (-122.4194 37.7749)'
    """
    latitude = _to_float(lat, "lat")
    longitude = _to_float(lon, "lon")

    if not -MAX_LATITUDE <= latitude <= MAX_LATITUDE:
        raise ValueError(
            f"lat must be within [-{MAX_LATITUDE}, {MAX_LATITUDE}] degrees, "
            f"got {latitude!r} (arguments are (lat, lon), not (lon, lat))"
        )
    if not -MAX_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise ValueError(
            f"lon must be within [-{MAX_LONGITUDE}, {MAX_LONGITUDE}] degrees, "
            f"got {longitude!r}"
        )

    # WKT is x-then-y: longitude first, latitude second.
    return f"POINT ({_format_ordinate(longitude)} {_format_ordinate(latitude)})"
```