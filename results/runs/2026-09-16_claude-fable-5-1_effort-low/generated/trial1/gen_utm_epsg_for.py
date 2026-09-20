"""WGS 84 / UTM EPSG code for a WGS84 longitude/latitude.

Grid zones follow the Military Grid Reference System (MGRS), i.e. the
standard 6-degree UTM zones plus the published exceptions:

* Zone 32V is widened to cover south-west Norway (56N-64N, 3E-12E).
* Svalbard (72N-84N) uses only zones 31X, 33X, 35X and 37X.

The function is pure and importing the module has no side effects.
"""

from __future__ import annotations

__all__ = ["utm_epsg_for", "utm_zone_for"]


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into the half-open interval [-180, 180)."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def utm_zone_for(lon: float, lat: float) -> int:
    """Return the MGRS/UTM zone number (1-60) containing (lon, lat)."""
    lon = float(lon)
    lat = float(lat)
    if lat != lat or lon != lon:  # NaN
        raise ValueError("lon/lat must not be NaN")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")

    lon = _normalize_lon(lon)

    # Standard 6-degree zones; zone 60 covers [174, 180).
    zone = int((lon + 180.0) // 6.0) + 1
    if zone > 60:
        zone = 60

    # Exception 1: south-west Norway, latitude band V (56N-64N).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Exception 2: Svalbard, latitude band X (72N-84N).
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of WGS 84 / UTM for the grid zone containing (lon, lat).

    Northern hemisphere (lat >= 0) codes are 326xx, southern are 327xx,
    where xx is the zero-padded MGRS zone number.
    """
    zone = utm_zone_for(lon, lat)
    base = 32600 if float(lat) >= 0.0 else 32700
    return base + zone