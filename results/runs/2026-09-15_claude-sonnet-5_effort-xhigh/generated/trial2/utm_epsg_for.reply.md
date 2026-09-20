```python
"""Determine the WGS 84 / UTM EPSG code for a longitude/latitude pair.

Zone numbering follows the Military Grid Reference System (MGRS), including
its published exceptions around southwest Norway and Svalbard.
"""

from __future__ import annotations


def _normalize_longitude(lon: float) -> float:
    """Wrap longitude into the half-open range [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def _base_zone(lon: float) -> int:
    """Standard UTM zone number (1-60) for a normalized longitude, ignoring MGRS exceptions."""
    zone = int((lon + 180.0) // 6.0) + 1
    return min(max(zone, 1), 60)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the MGRS grid zone containing (lon, lat).

    Applies the MGRS grid zone exceptions: the widened zone 32 covering
    southwest Norway (56N-64N, 3E-12E) and the widened zones 31/33/35/37
    around Svalbard (72N-84N, 0E-42E), where zones 32/34/36 do not occur.
    """
    lon = _normalize_longitude(lon)

    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32
    elif 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            zone = 31
        elif lon < 21.0:
            zone = 33
        elif lon < 33.0:
            zone = 35
        else:
            zone = 37
    else:
        zone = _base_zone(lon)

    hemisphere_prefix = 326 if lat >= 0 else 327
    return hemisphere_prefix * 100 + zone
```