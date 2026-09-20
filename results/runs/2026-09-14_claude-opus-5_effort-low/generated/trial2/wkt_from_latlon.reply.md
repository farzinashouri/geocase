```python
"""Convert WGS84 latitude/longitude pairs into WKT POINT geometry.

Importing this module has no side effects.
"""

from __future__ import annotations

__all__ = ["wkt_from_latlon"]


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as (lat, lon).

    WKT stores coordinates in x/y order, so the longitude is written first:
    ``wkt_from_latlon(48.858, 2.294)`` -> ``'POINT (2.294 48.858)'``.

    Raises:
        TypeError: if either argument is not a real number.
        ValueError: if either argument is NaN/infinite or out of range.
    """
    lat = _as_finite_float(lat, "lat")
    lon = _as_finite_float(lon, "lon")

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be within [-90, 90], got {lat!r}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be within [-180, 180], got {lon!r}")

    return f"POINT ({_fmt(lon)} {_fmt(lat)})"


def _as_finite_float(value: object, name: str) -> float:
    import math

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _fmt(value: float) -> str:
    """Format a coordinate with full round-trip precision, no exponent."""
    text = f"{value:.17g}"
    if "e" in text or "E" in text:
        text = f"{value:.15f}".rstrip("0").rstrip(".")
    # Normalize negative zero so output stays readable in GIS tools.
    return "0" if text in ("-0", "-0.0") else text
```