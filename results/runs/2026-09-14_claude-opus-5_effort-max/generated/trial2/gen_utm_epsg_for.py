"""WGS 84 / UTM EPSG lookup using Military Grid Reference System zone numbering.

The MGRS divides the Earth between 80 deg S and 84 deg N into sixty 6 deg wide
longitudinal zones, numbered 1..60 eastward from the antimeridian, crossed by
latitude bands lettered C..X.  Two published exceptions perturb the regular
6 deg pattern:

* Band V (56 deg N to 64 deg N): zone 32 is widened westward to 3 deg E so that
  south-western Norway stays in one zone, correspondingly narrowing 31V.
* Band X (72 deg N to 84 deg N): zones 32, 34 and 36 are suppressed and zones
  31, 33, 35 and 37 are widened so that Svalbard stays in whole zones.

Only ``utm_epsg_for`` is public.  Importing the module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

#: EPSG code of WGS 84 / UTM zone 1N minus one, and likewise for the south.
_NORTHERN_BASE = 32600
_SOUTHERN_BASE = 32700

#: Latitude limits of the UTM grid: band C starts at 80 deg S, band X (which is
#: 12 deg tall rather than 8) ends at 84 deg N.  Outside them MGRS uses the
#: Universal Polar Stereographic grid, which has no UTM zone.
_MIN_LATITUDE = -80.0
_MAX_LATITUDE = 84.0

#: Band V exception: the half-open longitude span moved into zone 32.
_BAND_V_LATITUDES = (56.0, 64.0)
_BAND_V_EXCEPTION = (3.0, 12.0, 32)

#: Band X exceptions as (west edge inclusive, east edge exclusive, zone).
_BAND_X_LATITUDES = (72.0, 84.0)
_BAND_X_EXCEPTIONS = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)


def _wrap_longitude(lon: float) -> float:
    """Return ``lon`` wrapped into the half-open interval [-180, 180).

    Zones run half-open eastward, so the antimeridian itself belongs to zone 1
    whether it is spelled 180 or -180.
    """
    return (lon + 180.0) % 360.0 - 180.0


def _grid_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS zone number (1..60) for an already validated position."""
    if _BAND_V_LATITUDES[0] <= lat < _BAND_V_LATITUDES[1]:
        west, east, zone = _BAND_V_EXCEPTION
        if west <= lon < east:
            return zone
    elif _BAND_X_LATITUDES[0] <= lat <= _BAND_X_LATITUDES[1]:
        for west, east, zone in _BAND_X_EXCEPTIONS:
            if west <= lon < east:
                return zone

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Guard against a float landing exactly on 180 after wrapping.
    return min(max(zone, 1), 60)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS covering ``lon``, ``lat``.

    ``lon`` and ``lat`` are WGS 84 degrees.  The grid zone is chosen the way
    MGRS assigns them, including the band V (Norway) and band X (Svalbard)
    exceptions, so e.g. Bergen returns zone 32 rather than 31.  The result is
    ``326xx`` in the northern hemisphere and ``327xx`` in the southern, with
    ``xx`` the zone number; the equator itself counts as northern.

    Longitudes outside [-180, 180) are wrapped.  A latitude outside the UTM
    grid (below 80 deg S or above 84 deg N, where MGRS switches to the polar
    stereographic UPS grid) raises :class:`ValueError`, as does a non-finite
    coordinate.

    >>> utm_epsg_for(10.75, 59.91)    # Oslo, band V exception
    32632
    >>> utm_epsg_for(15.65, 78.22)    # Longyearbyen, band X exception
    32633
    >>> utm_epsg_for(-58.38, -34.60)  # Buenos Aires
    32721
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError("longitude and latitude must be finite numbers")
    if not _MIN_LATITUDE <= lat <= _MAX_LATITUDE:
        raise ValueError(
            "latitude {0!r} lies outside the UTM grid ({1} to {2} degrees); "
            "the polar regions use the UPS grid, which has no UTM zone".format(
                lat, _MIN_LATITUDE, _MAX_LATITUDE
            )
        )

    zone = _grid_zone_number(_wrap_longitude(lon), lat)
    return (_NORTHERN_BASE if lat >= 0.0 else _SOUTHERN_BASE) + zone