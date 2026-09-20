"""EPSG code of the WGS 84 / UTM zone that MGRS assigns to a WGS 84 point.

The Military Grid Reference System (MGRS) numbers UTM zones with the usual
6-degree scheme plus two published exceptions:

* Latitude band V (56N to 64N): zone 32 is widened to 3E-12E so that the
  south-west coast of Norway sits in one zone. Zone 31 shrinks to 0E-3E.
* Latitude band X (72N to 84N): zones 32, 34 and 36 are dropped around
  Svalbard. Zone 31 covers 0E-9E, 33 covers 9E-21E, 35 covers 21E-33E and
  37 covers 33E-42E.

EPSG codes are 326xx north of the equator (latitude >= 0) and 327xx south,
where xx is the zone number. Points outside 80S-84N have no UTM grid zone
(MGRS uses the polar stereographic UPS grids there) and raise ValueError.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for", "utm_zone_for"]

_MIN_LAT = -80.0  # southern limit of the UTM/MGRS grid zones
_MAX_LAT = 84.0  # northern limit of the UTM/MGRS grid zones


def _as_coordinates(lon: float, lat: float) -> tuple[float, float]:
    """Validate the inputs and return (lon, lat) as floats.

    Longitude is wrapped into [-180, 180]; +180 is kept as +180 so the
    antimeridian falls in zone 60 rather than zone 1.
    """
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(f"longitude and latitude must be finite, got {lon!r}, {lat!r}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude must be within [-90, 90], got {lat!r}")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"latitude {lat!r} lies outside the UTM/MGRS grid zones "
            f"({_MIN_LAT:g} to {_MAX_LAT:g}); polar regions use UPS"
        )
    if not -180.0 <= lon <= 180.0:
        lon = (lon + 180.0) % 360.0 - 180.0
    return lon, lat


def utm_zone_for(lon: float, lat: float) -> int:
    """Return the MGRS/UTM zone number (1-60) for a WGS 84 point.

    Includes the Norway (32V) and Svalbard (31X, 33X, 35X, 37X) exceptions.
    """
    lon, lat = _as_coordinates(lon, lat)

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    zone = max(1, min(zone, 60))

    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        # Band V: zone 32 widened westward to 3E, covering south-west Norway.
        zone = 32
    elif lat >= 72.0 and 0.0 <= lon < 42.0:
        # Band X: zones 32, 34 and 36 do not exist; their neighbours widen.
        if lon < 9.0:
            zone = 31
        elif lon < 21.0:
            zone = 33
        elif lon < 33.0:
            zone = 35
        else:
            zone = 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the MGRS grid zone.

    Args:
        lon: WGS 84 longitude in decimal degrees (east positive).
        lat: WGS 84 latitude in decimal degrees (north positive).

    Returns:
        ``32600 + zone`` for the northern hemisphere (latitude >= 0) or
        ``32700 + zone`` for the southern hemisphere.

    Raises:
        ValueError: if a coordinate is not finite, the latitude is outside
            [-90, 90], or the point lies outside the UTM grid (80S to 84N).
    """
    lon, lat = _as_coordinates(lon, lat)
    zone = utm_zone_for(lon, lat)
    return (32600 if lat >= 0.0 else 32700) + zone