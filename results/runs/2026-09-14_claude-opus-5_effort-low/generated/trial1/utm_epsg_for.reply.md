```python
"""UTM EPSG lookup for WGS 84 coordinates, using MGRS grid-zone assignment.

The zone number follows the regular 6-degree scheme except for the published
grid exceptions around south-west Norway (32V) and Svalbard (band X).
"""

from __future__ import annotations

__all__ = ["utm_epsg_for"]


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    lon = float(lon)
    if lon != lon:  # NaN
        raise ValueError("longitude must be a finite number")
    return (lon + 180.0) % 360.0 - 180.0


def _zone_number(lon: float, lat: float) -> int:
    """MGRS grid-zone number for a normalized longitude and a valid latitude."""
    zone = int((lon + 180.0) // 6.0) + 1
    if zone > 60:  # only reachable for lon exactly at the wrap boundary
        zone = 60

    # South-west Norway: zone 32 is widened at the expense of zone 31.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Svalbard: zones 32, 34 and 36 are dropped; 31, 33, 35, 37 are widened.
    if 72.0 <= lat <= 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    return zone


def utm_epsg_for(lon, lat) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing ``(lon, lat)``.

    Codes are 326xx north of the equator and 327xx south of it, with ``xx``
    the MGRS grid-zone number (including the Norway and Svalbard exceptions).

    Raises ``ValueError`` if the latitude falls outside the UTM domain
    (80 degrees south to 84 degrees north).
    """
    lat = float(lat)
    if lat != lat:  # NaN
        raise ValueError("latitude must be a finite number")
    if not -80.0 <= lat <= 84.0:
        raise ValueError(
            "latitude %r is outside the UTM domain of -80..84 degrees" % (lat,)
        )

    lon = _normalize_lon(lon)
    zone = _zone_number(lon, lat)
    base = 32600 if lat >= 0.0 else 32700
    return base + zone
```