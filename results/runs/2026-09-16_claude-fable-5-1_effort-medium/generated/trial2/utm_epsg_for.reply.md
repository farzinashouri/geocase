```python
"""WGS 84 / UTM EPSG code lookup using MGRS grid-zone numbering.

The Military Grid Reference System divides the UTM latitude range
(80°S to 84°N) into 60 six-degree longitude zones, with two published
exceptions to the regular numbering:

* Zone 32V is widened to cover south-west Norway: for latitudes in
  [56°N, 64°N) the zone spans longitudes [3°E, 12°E).
* Around Svalbard, for latitudes in [72°N, 84°N], zones 32, 34 and 36
  are removed and zones 31, 33, 35 and 37 are widened to span
  [0°E, 9°E), [9°E, 21°E), [21°E, 33°E) and [33°E, 42°E) respectively.

EPSG codes are 326xx for the northern hemisphere and 327xx for the
southern, where xx is the two-digit zone number.
"""

from __future__ import annotations

import math

__all__ = ["utm_zone_number", "utm_epsg_for"]

_UTM_LAT_MIN = -80.0
_UTM_LAT_MAX = 84.0


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into the half-open range [-180, 180].

    The value 180 is kept as 180 (rather than wrapped to -180) so that
    the antimeridian resolves to zone 60, matching common practice.
    """
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    return wrapped


def utm_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS/UTM grid zone number (1-60) containing (lon, lat).

    Raises ValueError if latitude is outside the UTM range [-80, 84]
    (those areas belong to the UPS grids, which have no UTM zone).
    """
    lon = float(lon)
    lat = float(lat)
    if math.isnan(lon) or math.isnan(lat):
        raise ValueError("longitude and latitude must not be NaN")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"latitude {lat!r} is outside [-90, 90]")
    if not (_UTM_LAT_MIN <= lat <= _UTM_LAT_MAX):
        raise ValueError(
            f"latitude {lat!r} is outside the UTM range "
            f"[{_UTM_LAT_MIN:g}, {_UTM_LAT_MAX:g}] (polar UPS region)"
        )
    lon = _normalize_longitude(lon)

    # Published MGRS exception: south-west Norway (band V), zone 32 widened.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Published MGRS exception: Svalbard (band X).
    if 72.0 <= lat <= _UTM_LAT_MAX and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if zone > 60:  # lon == 180 exactly
        zone = 60
    if zone < 1:
        zone = 1
    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code (int) of the WGS 84 / UTM CRS for (lon, lat).

    Zones follow MGRS numbering, including the Norway and Svalbard
    exceptions. Northern-hemisphere codes are 326xx; southern are 327xx.
    Latitude 0 is treated as northern.
    """
    zone = utm_zone_number(lon, lat)
    base = 32600 if float(lat) >= 0.0 else 32700
    return base + zone
```