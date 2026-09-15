```python
"""Build WKT ``POINT`` strings from WGS84 latitude/longitude pairs.

The public entry point takes ``(lat, lon)`` because that is the order
user-facing APIs conventionally use, but WKT is an ``(x, y)`` format: for
geographic coordinates that means ``POINT(longitude latitude)``. The swap
happens here so callers never have to think about it.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

# Number of decimal places kept in the output. Seven places is roughly
# 1 cm at the equator -- finer than WGS84 itself is meaningful -- while
# avoiding the float noise that ``repr`` would expose.
_PRECISION = 7


def _coerce(value: object, name: str) -> float:
    """Return ``value`` as a finite float or raise ``TypeError``/``ValueError``."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _format(value: float) -> str:
    """Format a coordinate without an exponent or a trailing '-0'."""
    text = f"{value:.{_PRECISION}f}".rstrip("0").rstrip(".")
    if text in ("-0", ""):
        text = "0"
    return text


def wkt_from_latlon(lat, lon) -> str:
    """Return the WKT ``POINT`` for a WGS84 location.

    Args:
        lat: Latitude in degrees, in ``[-90, 90]``.
        lon: Longitude in degrees, in ``[-180, 180]``.

    Returns:
        A WKT point such as ``"POINT (13.3888595 52.5170365)"``. Note the
        axis order: WKT is ``x y``, so longitude is written first.

    Raises:
        TypeError: If either argument is not a real number.
        ValueError: If either argument is non-finite or out of range.
    """
    latitude = _coerce(lat, "lat")
    longitude = _coerce(lon, "lon")

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"lat must be within [-90, 90] degrees, got {latitude!r}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"lon must be within [-180, 180] degrees, got {longitude!r}")

    return f"POINT ({_format(longitude)} {_format(latitude)})"
```