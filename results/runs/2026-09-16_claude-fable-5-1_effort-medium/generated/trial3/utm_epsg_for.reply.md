```python
"""Compute the WGS 84 / UTM EPSG code for a WGS84 longitude/latitude.

Zone numbering follows the Military Grid Reference System (MGRS), including
the published grid exceptions for southern Norway (zone 32V is widened) and
Svalbard (zones 32X, 34X and 36X are omitted; 31X, 33X, 35X and 37X are widened).
"""

import math

__all__ = ["utm_zone_number", "utm_epsg_for"]


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into the half-open range [-180, 180)."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def utm_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS/UTM zone number (1-60) containing the given point."""
    lon = _normalize_longitude(lon)

    # Southern Norway exception: zone 32V is extended west to 3E between 56N and 64N.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Svalbard exception: between 72N and 84N, zones 32, 34 and 36 do not exist.
    if 72.0 <= lat <= 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Guard against floating-point edge cases at the antimeridian.
    return min(max(zone, 1), 60)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the zone containing (lon, lat).

    Codes are 326xx for the northern hemisphere (lat >= 0) and 327xx for the
    southern hemisphere, where xx is the zone number.

    Raises:
        ValueError: if lon or lat is not a finite number, or lat is outside [-90, 90].
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError("longitude and latitude must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude {lat!r} is outside the range [-90, 90]")

    zone = utm_zone_number(lon, lat)
    base = 32600 if lat >= 0.0 else 32700
    return base + zone
```