```python
"""WKT helpers for WGS84 coordinates.

The public API takes coordinates in ``(lat, lon)`` order, which is how humans
and most user-facing APIs quote a location. WKT, however, is an *axis-ordered*
format whose axes follow the underlying geometry model: ``POINT (x y)``, i.e.
easting before northing, which for WGS84 (EPSG:4326) geographic coordinates
means longitude before latitude. Every mainstream GIS reader (PostGIS,
GDAL/OGR, shapely, QGIS) parses WKT that way, so the swap below is what makes
the output load at the right place on the map rather than at its transpose.
"""

from __future__ import annotations

__all__ = ["wkt_from_latlon"]


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT ``POINT`` for a WGS84 location given as latitude/longitude.

    Args:
        lat: Latitude in decimal degrees, in ``[-90, 90]``.
        lon: Longitude in decimal degrees, in ``[-180, 180]``.

    Returns:
        A WKT string of the form ``POINT (lon lat)`` — longitude first, per the
        x/y axis order that standard GIS tools expect for EPSG:4326.

    Raises:
        TypeError: If either argument is not a real number.
        ValueError: If either argument is NaN/infinite or out of range.

    Example:
        >>> wkt_from_latlon(48.8584, 2.2945)  # Eiffel Tower
        'POINT (2.2945 48.8584)'
    """
    lat = _validate("lat", lat, 90.0)
    lon = _validate("lon", lon, 180.0)
    return f"POINT ({_fmt(lon)} {_fmt(lat)})"


def _validate(name: str, value: object, limit: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if not -limit <= value <= limit:
        raise ValueError(f"{name} must be within [-{limit:g}, {limit:g}], got {value!r}")
    return value


def _fmt(value: float) -> str:
    """Render a coordinate without exponent notation or a trailing ``.0``."""
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-") else text
```