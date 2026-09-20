"""WGS 84 UTM EPSG lookup that honours the MGRS grid-zone exceptions.

``utm_epsg_for(lon, lat)`` returns the EPSG code of the ``WGS 84 / UTM zone NN{N,S}``
CRS whose grid zone contains the given point:

* ``32601``-``32660`` -- northern hemisphere, zones 1-60
* ``32701``-``32760`` -- southern hemisphere, zones 1-60

Zone numbers follow the regular six-degree scheme::

    zone = floor((lon + 180) / 6) + 1

apart from the two published irregularities that MGRS inherits from UTM:

South-west Norway (latitude band V, 56N <= lat < 64N)
    Zone 32 is widened westwards to 3E, so 3E <= lon < 12E falls in zone 32 and
    zone 31 keeps only 0 <= lon < 3E.

Svalbard (latitude band X, 72N <= lat <= 84N)
    Zones 32, 34 and 36 are not used; the odd zones on either side absorb them::

        0E  <= lon <  9E -> 31
        9E  <= lon < 21E -> 33
        21E <= lon < 33E -> 35
        33E <= lon < 42E -> 37

Longitudes are wrapped into [-180, 180), so 190 is treated as -170. Latitudes
outside [-80, 84] are rejected: the polar caps are covered by UPS, not UTM, and
so have no UTM grid zone (and no 326xx/327xx code) to return.

Examples::

    >>> utm_epsg_for(-73.98, 40.75)   # New York
    32618
    >>> utm_epsg_for(151.21, -33.87)  # Sydney
    32756
    >>> utm_epsg_for(5.0, 60.0)       # Bergen, Norway exception
    32632
    >>> utm_epsg_for(15.0, 78.0)      # Svalbard exception
    32633
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

# Latitude range covered by the MGRS grid zones / UTM proper: bands C..X.
_MIN_LAT = -80.0
_MAX_LAT = 84.0

# Norway exception, latitude band V.
_NORWAY_LAT = (56.0, 64.0)
_NORWAY_LON = (3.0, 12.0)
_NORWAY_ZONE = 32

# Svalbard exception, latitude band X: (lon_min, lon_max, zone).
_SVALBARD_LAT_MIN = 72.0
_SVALBARD_ZONES = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)

_NORTH_BASE = 32600
_SOUTH_BASE = 32700


def _wrap_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    wrapped = (lon + 180.0) % 360.0 - 180.0
    # Guard against the rounding case where a longitude just under 180 wraps
    # back onto +180.0 instead of -180.0.
    if wrapped >= 180.0:
        wrapped -= 360.0
    return wrapped


def _zone_number(lon: float, lat: float) -> int:
    """Grid-zone number for an already-wrapped, already-validated position."""
    if _NORWAY_LAT[0] <= lat < _NORWAY_LAT[1] and _NORWAY_LON[0] <= lon < _NORWAY_LON[1]:
        return _NORWAY_ZONE

    if lat >= _SVALBARD_LAT_MIN:
        for lon_min, lon_max, zone in _SVALBARD_ZONES:
            if lon_min <= lon < lon_max:
                return zone

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Only reachable through floating-point slop at the antimeridian.
    return min(max(zone, 1), 60)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing ``(lon, lat)``.

    Parameters
    ----------
    lon:
        WGS 84 longitude in decimal degrees. Values outside [-180, 180) are
        wrapped rather than rejected.
    lat:
        WGS 84 latitude in decimal degrees, within [-80, 84].

    Returns
    -------
    int
        ``32600 + zone`` for ``lat >= 0``, ``32700 + zone`` otherwise, with the
        zone number assigned as in MGRS (including the Norway and Svalbard
        grid exceptions).

    Raises
    ------
    ValueError
        If either coordinate is not a finite number, or the latitude lies
        outside the UTM/MGRS range [-80, 84].
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError(f"lon and lat must be finite numbers, got ({lon!r}, {lat!r})")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"latitude {lat!r} is outside the UTM range [{_MIN_LAT}, {_MAX_LAT}]; "
            "the polar regions are covered by UPS, which has no UTM zone"
        )

    lon = _wrap_lon(lon)
    base = _NORTH_BASE if lat >= 0.0 else _SOUTH_BASE
    return base + _zone_number(lon, lat)