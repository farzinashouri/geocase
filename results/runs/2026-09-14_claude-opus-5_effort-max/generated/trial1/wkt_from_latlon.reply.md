WKT is X‑then‑Y, so a `(lat, lon)` input has to come out as `POINT (lon lat)` — that swap is the whole job, plus keeping full float precision (shapely's `.wkt` rounds to 6 decimals ≈ 11 cm, so I format the digits myself).

```python
"""Build WKT ``POINT`` strings from WGS84 latitude/longitude pairs.

The one thing worth care here is axis order.  User-facing APIs conventionally
hand over coordinates as ``(latitude, longitude)``, and EPSG:4326 itself
formally declares a (latitude, longitude) axis order.  WKT geometry, however,
is always written ``X Y`` -- for geographic coordinates that means
``POINT (longitude latitude)``.  Emitting ``POINT (lat lon)`` yields a string
that parses without complaint in every GIS tool and puts the point in the
wrong place (Paris lands in Somalia), so this module accepts ``(lat, lon)``
and swaps on the way out.

Plain WKT carries no CRS -- there is nowhere in the grammar to put one.
Consumers that need the CRS want either EWKT (``SRID=4326;POINT (...)``) or an
out-of-band declaration such as a ``.prj`` sidecar or a GeoPackage srs entry.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

MAX_ABS_LATITUDE = 90.0
MAX_ABS_LONGITUDE = 180.0


def _coerce_degrees(value, name: str, limit: float) -> float:
    """Return ``value`` as a finite float within ``[-limit, limit]`` degrees."""
    try:
        number = float(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    except ValueError as exc:
        raise ValueError(f"{name} must be a real number, got {value!r}") from exc

    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if abs(number) > limit:
        raise ValueError(
            f"{name} must be within [-{limit:g}, {limit:g}] degrees, got {number!r}"
        )
    if number == 0.0:
        number = 0.0  # collapse -0.0 so the output reads "0" rather than "-0"
    return number


def _format_degrees(value: float) -> str:
    """Render ``value`` as plain decimal text, without losing precision."""
    text = repr(value)  # shortest representation that round-trips the float
    if "e" in text or "E" in text:
        # Only sub-0.0001-degree magnitudes reach exponent form (millimetres
        # and below); some WKT readers reject it, so spell those out instead.
        text = f"{value:.17f}".rstrip("0")
        if text.endswith("."):
            text += "0"
    return text


def wkt_from_latlon(lat, lon) -> str:
    """Return the WGS84 location ``(lat, lon)`` as a WKT ``POINT``.

    Args:
        lat: Latitude in decimal degrees, within [-90, 90].
        lon: Longitude in decimal degrees, within [-180, 180].

    Returns:
        A WKT ``POINT`` in WKT's ``X Y`` order, i.e. ``POINT (lon lat)``.

    Raises:
        TypeError: If a coordinate is not a real number.
        ValueError: If a coordinate is NaN, infinite, or out of range.

    >>> wkt_from_latlon(48.8584, 2.2945)  # Eiffel Tower
    'POINT (2.2945 48.8584)'
    >>> wkt_from_latlon(-33.8568, 151.2153)  # Sydney Opera House
    'POINT (151.2153 -33.8568)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0.0 0.0)'
    """
    latitude = _coerce_degrees(lat, "lat", MAX_ABS_LATITUDE)
    longitude = _coerce_degrees(lon, "lon", MAX_ABS_LONGITUDE)
    # Longitude is X (easting), latitude is Y (northing).
    return f"POINT ({_format_degrees(longitude)} {_format_degrees(latitude)})"
```