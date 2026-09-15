```python
"""Build WKT ``POINT`` geometry from WGS84 latitude/longitude.

The argument order here (``lat``, ``lon``) is the order humans and most
user-facing APIs use.  WKT, however, is an ordered coordinate format whose
axes are x then y: for geographic coordinates that is **longitude first**,
latitude second.  Emitting ``POINT(lat lon)`` is the classic axis-order bug
-- it silently produces a valid-looking geometry in the wrong hemisphere (or
off the globe entirely) once loaded into PostGIS, GDAL, QGIS, or shapely.
So the single job of this module is to swap the order exactly once, here.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

# Number of significant decimal places kept in the output.  Seven decimal
# degrees is ~1 cm at the equator, which is finer than any WGS84 fix in
# practice while keeping the text short and diff-friendly.
_DECIMALS = 7


def _coerce(value: object, name: str) -> float:
    """Return ``value`` as a finite float, or raise ``TypeError``/``ValueError``."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _format(value: float) -> str:
    """Format a coordinate as a plain decimal string.

    ``repr`` would emit scientific notation for small magnitudes (``1e-07``),
    which is not valid WKT, and would keep a signed zero (``-0.0``).  Both are
    normalized away here.
    """
    text = f"{value:.{_DECIMALS}f}"
    # Trim trailing zeros but always leave at least one digit after the point.
    if "." in text:
        text = text.rstrip("0").rstrip(".") or "0"
    if text in ("-0", ""):
        text = "0"
    return text


def wkt_from_latlon(lat, lon) -> str:
    """Return the WKT ``POINT`` for a WGS84 position.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, in ``[-90, 90]``.
    lon:
        Longitude in decimal degrees, in ``[-180, 180]``.

    Returns
    -------
    str
        e.g. ``wkt_from_latlon(48.8584, 2.2945) -> 'POINT (2.2945 48.8584)'``
        -- note longitude first, as WKT requires.

    Raises
    ------
    TypeError
        If either argument is not a real number.
    ValueError
        If either argument is non-finite or outside its valid range.
    """
    latitude = _coerce(lat, "lat")
    longitude = _coerce(lon, "lon")

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"lat must be in [-90, 90] degrees, got {latitude!r}; "
            "arguments are (lat, lon) -- check the order"
        )
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(
            f"lon must be in [-180, 180] degrees, got {longitude!r}; "
            "arguments are (lat, lon) -- check the order"
        )

    # x = longitude, y = latitude.
    return f"POINT ({_format(longitude)} {_format(latitude)})"
```