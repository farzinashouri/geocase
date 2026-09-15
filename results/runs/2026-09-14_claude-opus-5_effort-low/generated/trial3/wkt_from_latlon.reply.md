```python
"""Build WKT POINT strings from WGS84 latitude/longitude pairs.

WKT stores coordinates in x/y (easting/northing) order, so a WGS84 point is
written as ``POINT (lon lat)`` even though the arguments arrive lat-first the
way user-facing APIs conventionally supply them.
"""

from __future__ import annotations

__all__ = ["wkt_from_latlon"]


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return the WKT ``POINT`` for a WGS84 location given as (lat, lon).

    Args:
        lat: Latitude in degrees, -90 to 90.
        lon: Longitude in degrees, -180 to 180.

    Returns:
        A WKT string such as ``"POINT (-122.4194 37.7749)"``, with the
        coordinates in WKT's x-then-y (lon, lat) order.

    Raises:
        TypeError: If either argument is not a real number.
        ValueError: If either argument is NaN/infinite or out of range.
    """
    lat = _as_degrees(lat, "lat")
    lon = _as_degrees(lon, "lon")

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be between -90 and 90 degrees, got {lat!r}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be between -180 and 180 degrees, got {lon!r}")

    return f"POINT ({_format(lon)} {_format(lat)})"


def _as_degrees(value: float, name: str) -> float:
    """Coerce a coordinate to a finite float, rejecting bools and non-numbers."""
    import math
    import numbers

    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")

    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _format(value: float) -> str:
    """Render a coordinate without an exponent, which WKT parsers may reject."""
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-") else text
```