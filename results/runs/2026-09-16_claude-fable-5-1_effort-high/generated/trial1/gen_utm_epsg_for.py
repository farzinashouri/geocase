"""WGS 84 / UTM EPSG code lookup using MGRS grid-zone numbering.

The zone number is the standard 6-degree UTM zone, except for the two
published MGRS grid exceptions:

* Norway: latitude band V (56N-64N), longitude 3E-12E is all zone 32.
* Svalbard: latitude band X (72N-84N) uses zones 31, 33, 35, 37 only,
  covering 0E-9E, 9E-21E, 21E-33E and 33E-42E respectively.

EPSG codes are 326xx (northern hemisphere) and 327xx (southern), where xx
is the two-digit zone number. Latitudes outside the UTM/MGRS domain
(south of 80S or north of 84N, which fall in the UPS polar system) raise
``ValueError``.
"""

from __future__ import annotations

import math

__all__ = ["utm_zone_number", "utm_epsg_for"]

_LAT_MIN = -80.0
_LAT_MAX = 84.0


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into the half-open range [-180, 180)."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def utm_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS/UTM grid zone number (1-60) for a WGS84 location."""
    lon = float(lon)
    lat = float(lat)
    if math.isnan(lon) or math.isnan(lat):
        raise ValueError("longitude and latitude must be finite numbers")
    if not (_LAT_MIN <= lat < _LAT_MAX):
        raise ValueError(
            f"latitude {lat} is outside the UTM/MGRS domain "
            f"[{_LAT_MIN}, {_LAT_MAX}); use UPS for polar regions"
        )

    lon = _normalize_lon(lon)

    # Svalbard exception (latitude band X, 72N-84N).
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            return 31
        if 9.0 <= lon < 21.0:
            return 33
        if 21.0 <= lon < 33.0:
            return 35
        if 33.0 <= lon < 42.0:
            return 37

    # Norway exception (latitude band V, 56N-64N).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Guard against floating-point rounding at the upper edge.
    return max(1, min(60, zone))


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing (lon, lat).

    Parameters
    ----------
    lon : float
        WGS84 longitude in decimal degrees (any value; wrapped to [-180, 180)).
    lat : float
        WGS84 latitude in decimal degrees, in [-80, 84).

    Returns
    -------
    int
        326xx for the northern hemisphere (latitude >= 0), 327xx for the
        southern, where xx is the MGRS grid zone number.
    """
    zone = utm_zone_number(lon, lat)
    base = 32600 if float(lat) >= 0.0 else 32700
    return base + zone