"""WGS 84 / UTM EPSG code lookup with MGRS grid-zone exceptions.

Zone numbering follows the Military Grid Reference System: 60 six-degree
zones counted eastward from 180°W, with the published exceptions for
southern Norway (zone 32V widened to cover 3°E–12°E between 56°N and 64°N)
and Svalbard (zones 31X, 33X, 35X, 37X covering 0°E–42°E between 72°N and
84°N, with 32X, 34X, 36X unused).
"""

import math


def _normalize_lon(lon):
    """Wrap longitude into the half-open interval [-180, 180)."""
    lon = ((lon + 180.0) % 360.0) - 180.0
    return lon


def utm_zone_for(lon, lat):
    """Return the MGRS/UTM zone number (1-60) containing (lon, lat)."""
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError("lon and lat must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be within [-90, 90]")

    lon = _normalize_lon(lon)
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    zone = min(max(zone, 1), 60)

    # Southern Norway exception: band V (56N-64N), zone 32 extends west to 3E.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Svalbard exception: band X (72N-84N), zones 32, 34, 36 are not used.
    if 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            zone = 31
        elif lon < 21.0:
            zone = 33
        elif lon < 33.0:
            zone = 35
        else:
            zone = 37

    return zone


def utm_epsg_for(lon, lat):
    """Return the EPSG code (int) of WGS 84 / UTM for the MGRS zone at (lon, lat).

    Northern hemisphere (lat >= 0) codes are 326xx, southern are 327xx,
    where xx is the zero-padded zone number.
    """
    zone = utm_zone_for(lon, lat)
    base = 32600 if float(lat) >= 0.0 else 32700
    return base + zone


__all__ = ["utm_epsg_for", "utm_zone_for"]