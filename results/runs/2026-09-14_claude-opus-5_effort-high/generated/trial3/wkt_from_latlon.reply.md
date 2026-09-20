```python
"""Build WKT ``POINT`` geometries from WGS84 latitude/longitude pairs.

The one real trap here is axis order. Human-facing APIs quote coordinates as
``lat, lon`` (as this function's signature does), but WKT — and every GIS tool
that reads it — is Cartesian: ``POINT (X Y)``, i.e. ``POINT (lon lat)``.
Emitting ``POINT (lat lon)`` produces a string that parses fine and silently
lands in the wrong place (or off the globe entirely, for any longitude beyond
±90). So this module swaps the order on the way out.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

# 9 decimal places is ~0.1 mm at the equator: well beyond WGS84's meaningful
# precision, and short enough to avoid printing float noise.
_DECIMALS = 9


def _coerce(value: object, name: str) -> float:
    """Return ``value`` as a finite float, or raise a descriptive error."""
    if isinstance(value, bool):
        # bool is an int subclass; accepting it here is never what the caller meant.
        raise TypeError(f"{name} must be a real number, got bool")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {number!r}")
    return number


def _format(value: float) -> str:
    """Format a coordinate as a plain decimal (never scientific notation).

    ``repr(1e-7)`` is ``'1e-07'``, which several WKT readers reject, so fixed
    notation is used and trailing zeros are trimmed for readability.
    """
    text = f"{value:.{_DECIMALS}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):  # normalize -0.0 and values that round to zero
        text = "0"
    return text


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return the WKT ``POINT`` for a WGS84 position given as latitude, longitude.

    Args:
        lat: Latitude in decimal degrees, within [-90, 90].
        lon: Longitude in decimal degrees, within [-180, 180].

    Returns:
        A WKT string in ``POINT (lon lat)`` axis order — the order standard GIS
        tools expect — e.g. ``wkt_from_latlon(48.8584, 2.2945)`` gives
        ``'POINT (2.2945 48.8584)'``.

    Raises:
        TypeError: If either argument is not a real number.
        ValueError: If either argument is non-finite or out of range.
    """
    latitude = _coerce(lat, "lat")
    longitude = _coerce(lon, "lon")

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"lat must be within [-90, 90] degrees, got {latitude!r} "
            "(arguments are (lat, lon) — check the order)"
        )
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(
            f"lon must be within [-180, 180] degrees, got {longitude!r} "
            "(arguments are (lat, lon) — check the order)"
        )

    return f"POINT ({_format(longitude)} {_format(latitude)})"
```