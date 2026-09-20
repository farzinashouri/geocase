"""UTM EPSG lookup for WGS 84, following MGRS grid-zone assignment.

``utm_epsg_for(lon, lat)`` maps a WGS84 geographic coordinate to the EPSG code
of the WGS 84 / UTM zone whose MGRS grid zone contains it.  The MGRS zone
numbering includes the two published exceptions to the regular 6-degree
scheme: the widened zone 32V off southwest Norway, and the four widened
Svalbard zones in band X (31, 33, 35, 37, with zones 32, 34 and 36 absent).

EPSG codes are 326xx north of the equator and 327xx south of it, where ``xx``
is the two-digit zone number.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for", "utm_zone_for"]

#: Southern limit of MGRS latitude band C.
MIN_LATITUDE = -80.0

#: Northern limit of MGRS latitude band X.
MAX_LATITUDE = 84.0

_EPSG_UTM_NORTH_BASE = 32600
_EPSG_UTM_SOUTH_BASE = 32700

# Svalbard (band X) exception: (eastern limit of the zone, zone number).
# Zone boundaries at 0, 9, 21, 33 and 42 degrees east; zones 32, 34 and 36
# are not used in band X.
_SVALBARD_ZONES = ((9.0, 31), (21.0, 33), (33.0, 35), (42.0, 37))


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into the half-open interval [-180, 180)."""
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0
    return wrapped - 180.0


def utm_zone_for(lon: float, lat: float) -> int:
    """Return the MGRS/UTM zone number (1-60) containing ``lon``, ``lat``."""
    lon = float(lon)
    lat = float(lat)

    if math.isnan(lon) or math.isnan(lat) or math.isinf(lon) or math.isinf(lat):
        raise ValueError("longitude and latitude must be finite numbers")
    if not (MIN_LATITUDE <= lat <= MAX_LATITUDE):
        raise ValueError(
            "latitude {0!r} lies outside the UTM/MGRS domain "
            "[{1}, {2}]; the polar regions use UPS instead".format(
                lat, MIN_LATITUDE, MAX_LATITUDE
            )
        )

    lon = _normalize_longitude(lon)

    # Regular assignment: 60 zones of 6 degrees starting at 180 degrees west.
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if zone > 60:  # guards lon values rounding up onto the 180 seam
        zone = 60

    # Exception 1: zone 32V is widened westwards to 3 degrees east, at the
    # expense of zone 31V, over band V (56 <= lat < 64).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Exception 2: Svalbard, band X (72 <= lat <= 84).
    if lat >= 72.0 and 0.0 <= lon < 42.0:
        for eastern_limit, svalbard_zone in _SVALBARD_ZONES:
            if lon < eastern_limit:
                return svalbard_zone

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for ``lon``, ``lat``.

    Parameters
    ----------
    lon, lat:
        WGS84 longitude and latitude in decimal degrees.  Longitudes outside
        [-180, 180) are wrapped; latitudes outside [-80, 84] raise
        ``ValueError`` because UTM is undefined there.

    Returns
    -------
    int
        ``326xx`` for northern-hemisphere zones, ``327xx`` for southern ones.
    """
    zone = utm_zone_for(lon, lat)
    base = _EPSG_UTM_NORTH_BASE if float(lat) >= 0.0 else _EPSG_UTM_SOUTH_BASE
    return base + zone