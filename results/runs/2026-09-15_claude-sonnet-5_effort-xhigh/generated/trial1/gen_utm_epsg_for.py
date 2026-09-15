"""Determine the WGS 84 / UTM EPSG code for a geographic coordinate.

Zone assignment follows the Military Grid Reference System (MGRS), including
the published grid zone exceptions around Norway and Svalbard.
"""

import math


def _wrap_longitude(lon: float) -> float:
    """Wrap longitude into the half-open range [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def _base_zone_number(lon_norm: float) -> int:
    """Standard UTM zone number (1-60) for a longitude already in [-180, 180)."""
    zone = int(math.floor((lon_norm + 180.0) / 6.0)) + 1
    if zone < 1:
        zone = 1
    elif zone > 60:
        zone = 60
    return zone


def _mgrs_zone_number(lon: float, lat: float) -> int:
    """MGRS zone number, applying the Norway and Svalbard grid exceptions."""
    lon_norm = _wrap_longitude(lon)
    zone = _base_zone_number(lon_norm)

    # Norway exception: zone 32 is widened to cover 3E-12E between 56N-64N,
    # absorbing territory that would otherwise belong to zone 31.
    if 56.0 <= lat < 64.0 and 3.0 <= lon_norm < 12.0:
        return 32

    # Svalbard exception: between 72N-84N, only zones 31, 33, 35, 37 exist,
    # each widened to 12 degrees of longitude.
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon_norm < 9.0:
            return 31
        if 9.0 <= lon_norm < 21.0:
            return 33
        if 21.0 <= lon_norm < 33.0:
            return 35
        if 33.0 <= lon_norm < 42.0:
            return 37
        return zone

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the MGRS grid zone
    containing (lon, lat).

    Northern hemisphere zones use codes 326xx; southern hemisphere zones
    (lat < 0) use codes 327xx, where xx is the two-digit zone number.
    """
    zone = _mgrs_zone_number(lon, lat)
    hemisphere_prefix = 326 if lat >= 0 else 327
    return hemisphere_prefix * 100 + zone