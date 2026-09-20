"""WGS 84 / UTM EPSG code lookup using MGRS grid-zone assignment.

The zone number is the standard 6-degree UTM zone, with the two
published MGRS grid exceptions applied:

* Southern Norway (56N-64N, 3E-12E) lies entirely in zone 32.
* Svalbard (72N-84N, 0E-42E) uses only the odd zones 31, 33, 35, 37.

Northern-hemisphere codes are 326xx; southern-hemisphere codes are 327xx.
Importing this module has no side effects.
"""

from __future__ import annotations

import math


def _utm_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS/UTM zone number (1-60) for a WGS84 lon/lat."""
    # Normalise longitude to the half-open interval [-180, 180).
    lon = ((lon + 180.0) % 360.0) - 180.0

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    zone = max(1, min(60, zone))

    # Exception 1: southern Norway, grid zone 32V is widened westward.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Exception 2: Svalbard, zones 32, 34 and 36 are omitted.
    if 72.0 <= lat <= 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing (lon, lat).

    Parameters
    ----------
    lon : float
        WGS84 longitude in decimal degrees.
    lat : float
        WGS84 latitude in decimal degrees.

    Returns
    -------
    int
        326xx for northern-hemisphere zones, 327xx for southern-hemisphere
        zones, where xx is the MGRS zone number (with grid exceptions).

    Raises
    ------
    ValueError
        If the inputs are not finite numbers or latitude is out of range.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError("lon and lat must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude {lat!r} outside [-90, 90]")

    zone = _utm_zone_number(lon, lat)
    base = 32600 if lat >= 0.0 else 32700
    return base + zone


__all__ = ["utm_epsg_for"]