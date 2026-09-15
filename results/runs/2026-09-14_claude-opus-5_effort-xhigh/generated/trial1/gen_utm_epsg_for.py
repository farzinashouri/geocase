"""WGS 84 / UTM EPSG codes for MGRS grid zones.

``utm_epsg_for(lon, lat)`` maps a WGS84 geographic coordinate to the EPSG code
of the WGS 84 / UTM projected CRS whose zone contains it, following the zone
numbering used by the Military Grid Reference System.  That numbering is the
regular 6-degree partition of longitude *plus* the two published exceptions:

* Zone 32V (band V, 56N <= lat < 64N) is widened to cover 3E..12E so that
  south-western Norway falls in a single zone; zone 31V shrinks to 0E..3E.
* Over Svalbard (band X, 72N <= lat <= 84N) zones 32X, 34X and 36X are not
  used.  The odd zones on either side are widened instead:
  31X = 0E..9E, 33X = 9E..21E, 35X = 21E..33E, 37X = 33E..42E.

Zone boundaries are half-open on the east: a coordinate exactly on a meridian
that separates two zones belongs to the zone starting there.  The antimeridian
is normalised to -180, i.e. lon == 180 is zone 1.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["utm_zone_for", "utm_epsg_for"]

# Latitude limits of the MGRS grid-zone (UTM) area: band C starts at 80S,
# band X ends at 84N.  Outside this range MGRS uses the UPS grid, which has
# no UTM zone and therefore no 326xx/327xx code.
_MIN_LAT = -80.0
_MAX_LAT = 84.0

# Band V exception (south-western Norway).
_BAND_V_MIN_LAT = 56.0
_BAND_V_MAX_LAT = 64.0

# Band X exception (Svalbard), as (west_lon, east_lon, zone) with the eastern
# bound exclusive.  Longitudes in band X outside 0E..42E are unexceptional.
_BAND_X_MIN_LAT = 72.0
_SVALBARD_ZONES = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)

_NORTH_EPSG_BASE = 32600
_SOUTH_EPSG_BASE = 32700


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    wrapped = (lon + 180.0) % 360.0 - 180.0
    # Float rounding can push values that are barely below a full turn onto the
    # upper bound; the antimeridian belongs to zone 1, so fold it back.
    if wrapped >= 180.0:
        wrapped = -180.0
    return wrapped


def utm_zone_for(lon: float, lat: float) -> int:
    """Return the MGRS/UTM zone number (1..60) containing ``lon``/``lat``.

    Raises:
        ValueError: if either coordinate is not finite, if ``lat`` is outside
            [-90, 90], or if the point lies in the polar (UPS) area where no
            UTM zone is defined.
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError("lon and lat must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude {lat} is outside [-90, 90]")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"latitude {lat} is outside the UTM/MGRS area "
            f"[{_MIN_LAT}, {_MAX_LAT}]; the poles use the UPS grid, "
            "which has no UTM zone"
        )

    lon = _normalize_lon(lon)

    if _BAND_X_MIN_LAT <= lat:
        for west, east, zone in _SVALBARD_ZONES:
            if west <= lon < east:
                return zone
    elif _BAND_V_MIN_LAT <= lat < _BAND_V_MAX_LAT and 3.0 <= lon < 12.0:
        return 32

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Guard against rounding at the extremes of the wrapped range.
    return min(60, max(1, zone))


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing ``lon``/``lat``.

    Northern-hemisphere codes are 326xx and southern-hemisphere codes 327xx,
    where ``xx`` is the MGRS zone number.  The equator belongs to the north.

    Args:
        lon: WGS84 longitude in degrees; wrapped into [-180, 180).
        lat: WGS84 latitude in degrees.

    Returns:
        The EPSG code as an ``int``, e.g. ``32632`` for Bergen, Norway.

    Raises:
        ValueError: see :func:`utm_zone_for`.
    """
    zone = utm_zone_for(lon, lat)
    base = _NORTH_EPSG_BASE if float(lat) >= 0.0 else _SOUTH_EPSG_BASE
    return base + zone