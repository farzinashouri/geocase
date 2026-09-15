```python
"""UTM CRS lookup for WGS 84 longitude/latitude positions.

`utm_epsg_for(lon, lat)` returns the EPSG code of the *WGS 84 / UTM zone N*
(326xx) or *zone S* (327xx) coordinate reference system whose zone contains the
given point, using the zone numbering of the Military Grid Reference System —
that is, the regular 6°-wide zones plus the two published grid exceptions:

* **Zone 32V (south-west Norway).**  In latitude band V (56°N ≤ lat < 64°N),
  zone 32 is widened westward to 3°E, so 3°E ≤ lon < 12°E maps to zone 32 and
  zone 31V is correspondingly narrowed to 0°–3°E.
* **Svalbard (latitude band X, 72°N ≤ lat < 84°N).**  Zones 32, 34 and 36 are
  not used; the remaining zones are widened to cover 0°–42°E as
  31X: 0°–9°E, 33X: 9°–21°E, 35X: 21°–33°E, 37X: 33°–42°E.

Longitudes are normalised to [-180°, 180°), so ±180° both fall in zone 1.
Latitude 0 is treated as northern hemisphere (MGRS band N starts at the
equator).  Latitudes outside the MGRS coverage of 80°S–84°N — where the
grid uses the polar UPS zones rather than UTM — have no grid-zone exception
applied and simply receive the UTM zone implied by their longitude.

This module is pure standard library and importing it has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

_ZONE_WIDTH_DEG = 6.0
_NUM_ZONES = 60

# EPSG bases: 32601..32660 north, 32701..32760 south.
_NORTH_BASE = 32600
_SOUTH_BASE = 32700

# Latitude band V, where zone 32 is widened westward at the expense of 31.
_BAND_V_MIN_LAT = 56.0
_BAND_V_MAX_LAT = 64.0
_ZONE_32V_MIN_LON = 3.0
_ZONE_32V_MAX_LON = 12.0

# Latitude band X (Svalbard), where zones 32/34/36 are dropped.
_BAND_X_MIN_LAT = 72.0
_BAND_X_MAX_LAT = 84.0
_SVALBARD_MAX_LON = 42.0
# (exclusive eastern limit of the widened zone, zone number)
_SVALBARD_ZONES = ((9.0, 31), (21.0, 33), (33.0, 35), (42.0, 37))


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _regular_zone(lon: float) -> int:
    """Zone number from the plain 6°-wide scheme, for a normalised longitude."""
    zone = int((lon + 180.0) // _ZONE_WIDTH_DEG) + 1
    # Guards against float round-off at the eastern edge of zone 60.
    return min(zone, _NUM_ZONES)


def _zone_number(lon: float, lat: float) -> int:
    """MGRS grid-zone number for a normalised longitude and a latitude."""
    if _BAND_V_MIN_LAT <= lat < _BAND_V_MAX_LAT:
        if _ZONE_32V_MIN_LON <= lon < _ZONE_32V_MAX_LON:
            return 32

    if _BAND_X_MIN_LAT <= lat < _BAND_X_MAX_LAT:
        if 0.0 <= lon < _SVALBARD_MAX_LON:
            for max_lon, zone in _SVALBARD_ZONES:
                if lon < max_lon:
                    return zone

    return _regular_zone(lon)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the zone holding a point.

    Parameters
    ----------
    lon, lat:
        WGS 84 longitude and latitude in decimal degrees.  Longitude may be
        given outside [-180, 180] and is wrapped.

    Returns
    -------
    int
        32601-32660 for northern-hemisphere zones, 32701-32760 for southern.

    Raises
    ------
    ValueError
        If either coordinate is not finite, or the latitude is outside
        [-90, 90].
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError(f"lon and lat must be finite: got ({lon!r}, {lat!r})")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range [-90, 90]: {lat!r}")

    lon = _normalize_longitude(lon)
    zone = _zone_number(lon, lat)
    base = _NORTH_BASE if lat >= 0.0 else _SOUTH_BASE
    return base + zone
```