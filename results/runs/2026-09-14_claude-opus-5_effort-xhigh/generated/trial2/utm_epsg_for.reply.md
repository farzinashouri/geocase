```python
"""WGS 84 / UTM CRS lookup for MGRS grid zones.

``utm_epsg_for(lon, lat)`` maps a WGS 84 geographic position to the EPSG code
of the projected CRS for the MGRS grid zone that contains it: ``326xx`` in the
northern hemisphere, ``327xx`` in the southern, with ``xx`` the zone number.

Zone numbers follow the Military Grid Reference System, so the two published
exceptions to the regular 6-degree lune scheme are honoured:

* Band V (56N-64N): zone 32 is widened westward to 3E, at the expense of
  zone 31, so that south-western Norway sits in a single zone.
* Band X (72N-84N, Svalbard): zones 32, 34 and 36 are not used; zones 31, 33,
  35 and 37 widen to cover 0E-9E, 9E-21E, 21E-33E and 33E-42E respectively.

The MGRS grid zones cover 80S to 84N only; outside that range UTM is not
defined (the poles are covered by UPS) and ``ValueError`` is raised.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

_MIN_LAT = -80.0
_MAX_LAT = 84.0

_NORTH_BASE = 32600
_SOUTH_BASE = 32700

# Svalbard exception, as (west_deg, east_deg, zone) half-open in longitude.
_SVALBARD_ZONES = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)


def _wrap_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180), so 180E and 180W both mean zone 1."""
    return (lon + 180.0) % 360.0 - 180.0


def utm_epsg_for(lon, lat) -> int:
    """Return the EPSG code of the WGS 84 / UTM zone containing ``lon, lat``.

    Parameters
    ----------
    lon, lat:
        WGS 84 longitude and latitude in decimal degrees. Longitude is wrapped
        into [-180, 180); latitude must lie within the MGRS grid zone extent
        of 80S to 84N.

    Raises
    ------
    ValueError
        If either argument is not a finite number, or the latitude falls
        outside the MGRS grid zones.
    """
    lon = float(lon)
    lat = float(lat)

    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError("lon and lat must be finite numbers")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"latitude {lat} is outside the MGRS UTM grid zones "
            f"({_MIN_LAT} to {_MAX_LAT} degrees)"
        )

    lon = _wrap_lon(lon)

    # Regular scheme: 60 lunes of 6 degrees, zone 1 starting at 180W.
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if zone > 60:  # only reachable through floating-point slop at 180E
        zone = 60

    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32
    elif lat >= 72.0:
        for west, east, svalbard_zone in _SVALBARD_ZONES:
            if west <= lon < east:
                zone = svalbard_zone
                break

    return (_NORTH_BASE if lat >= 0.0 else _SOUTH_BASE) + zone
```