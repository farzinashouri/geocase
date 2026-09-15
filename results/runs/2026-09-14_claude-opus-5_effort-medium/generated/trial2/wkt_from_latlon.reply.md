The key correctness point: WKT is axis-order `POINT(x y)` = `POINT(lon lat)`, so the inputs get swapped on output.

```python
"""Build WKT POINT geometry from WGS84 latitude/longitude.

Note on axis order: this function takes ``(lat, lon)`` because that is the
order humans and most user-facing APIs quote coordinates in. WKT, however, is
defined in ``(x, y)`` order, which for WGS84 (EPSG:4326 as handled by GDAL,
PostGIS, shapely, GeoJSON, and essentially every GIS tool that consumes WKT)
means ``(longitude, latitude)``. The arguments are therefore swapped on output;
emitting ``POINT(lat lon)`` is the single most common way to produce a WKT
string that parses fine but plots in the wrong place (or off the globe).
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0


def _coerce(value: float, name: str) -> float:
    """Return ``value`` as a finite float, or raise a helpful error."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {number!r}")
    return number


def _format(number: float) -> str:
    """Format a coordinate without scientific notation or a trailing '.0'.

    ``repr`` gives the shortest round-trippable decimal, but it switches to
    exponent form for small magnitudes (e.g. ``1e-05``), which many WKT
    parsers reject. ``repr`` is used where it is safe and a fixed-point
    fallback is used where it is not.
    """
    text = repr(number)
    if "e" in text or "E" in text:
        text = f"{number:.10f}".rstrip("0")
        if text.endswith("."):
            text += "0"
    if text == "-0.0":
        text = "0.0"
    return text


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return the WKT ``POINT`` for a WGS84 latitude/longitude pair.

    Args:
        lat: Latitude in decimal degrees, in ``[-90, 90]``.
        lon: Longitude in decimal degrees, in ``[-180, 180]``.

    Returns:
        A WKT string such as ``'POINT (4.895168 52.370216)'`` — longitude
        first, as required by the WKT axis order for WGS84.

    Raises:
        TypeError: If a coordinate is not a real number.
        ValueError: If a coordinate is non-finite or out of range.

    >>> wkt_from_latlon(52.370216, 4.895168)
    'POINT (4.895168 52.370216)'
    """
    latitude = _coerce(lat, "lat")
    longitude = _coerce(lon, "lon")

    if not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
        raise ValueError(
            f"lat must be within [{MIN_LATITUDE}, {MAX_LATITUDE}] degrees, "
            f"got {latitude!r} (arguments are (lat, lon), not (lon, lat))"
        )
    if not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise ValueError(
            f"lon must be within [{MIN_LONGITUDE}, {MAX_LONGITUDE}] degrees, "
            f"got {longitude!r}"
        )

    return f"POINT ({_format(longitude)} {_format(latitude)})"
```