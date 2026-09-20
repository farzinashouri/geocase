```python
"""WGS 84 / UTM EPSG lookup for a geographic position.

`utm_epsg_for(lon, lat)` returns the EPSG code of the WGS 84 / UTM CRS whose
zone contains the given point, using Military Grid Reference System zone
numbering.  MGRS deviates from the plain six-degree rule in two places:

* Zone 32V (latitude band V, 56 <= lat < 64) is widened westward to 3 deg E,
  so that south-western Norway falls in a single zone; zone 31V is narrowed
  to 0..3 deg E accordingly.
* In latitude band X (72 <= lat < 84) zones 32, 34 and 36 are not used.  The
  space is taken up by widened zones 31X (0..9), 33X (9..21), 35X (21..33)
  and 37X (33..42), which keeps Svalbard whole.

Zone boundaries are treated as half-open intervals [west, east): a point
exactly on a meridian belongs to the zone east of it.  The module has no
import-time side effects and uses only the standard library.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

# EPSG code bases: 326xx north of the equator, 327xx south of it.
_EPSG_BASE_NORTH = 32600
_EPSG_BASE_SOUTH = 32700

# Latitude range covered by UTM / MGRS grid zones.  Outside this band the
# Universal Polar Stereographic system is used instead and there is no zone.
_MIN_LATITUDE = -80.0
_MAX_LATITUDE = 84.0

# Norway exception, latitude band V.
_BAND_V_MIN_LAT = 56.0
_BAND_V_MAX_LAT = 64.0

# Svalbard exception, latitude band X.
_BAND_X_MIN_LAT = 72.0
_BAND_X_MAX_LAT = 84.0

# (eastern limit, zone) pairs for band X, scanned west to east; longitudes at
# or beyond the last limit follow the ordinary six-degree rule.
_BAND_X_ZONES = ((9.0, 31), (21.0, 33), (33.0, 35), (42.0, 37))


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into [-180, 180).

    180 deg E and 180 deg W name the same meridian; it is the western edge of
    zone 1, so both map to -180.
    """
    return (lon + 180.0) % 360.0 - 180.0


def _zone_number(lon: float, lat: float) -> int:
    """MGRS grid zone number for a normalized longitude and a valid latitude."""
    if _BAND_X_MIN_LAT <= lat < _BAND_X_MAX_LAT:
        if 0.0 <= lon < _BAND_X_ZONES[-1][0]:
            for eastern_limit, zone in _BAND_X_ZONES:
                if lon < eastern_limit:
                    return zone
    elif _BAND_V_MIN_LAT <= lat < _BAND_V_MAX_LAT:
        if 3.0 <= lon < 12.0:
            return 32

    return int((lon + 180.0) // 6.0) + 1


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS covering ``(lon, lat)``.

    Args:
        lon: Longitude in degrees east of Greenwich (WGS 84).  Values outside
            [-180, 180) are wrapped.
        lat: Latitude in degrees north of the equator (WGS 84).

    Returns:
        326xx for the northern hemisphere (lat >= 0) or 327xx for the
        southern, where xx is the MGRS zone number.

    Raises:
        ValueError: if either coordinate is not a finite number, or if the
            latitude lies outside the [-80, 84] range covered by UTM.
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError(f"coordinates must be finite: lon={lon!r}, lat={lat!r}")
    if not _MIN_LATITUDE <= lat <= _MAX_LATITUDE:
        raise ValueError(
            f"latitude {lat!r} is outside the UTM range "
            f"[{_MIN_LATITUDE}, {_MAX_LATITUDE}]"
        )

    zone = _zone_number(_normalize_longitude(lon), lat)
    base = _EPSG_BASE_NORTH if lat >= 0.0 else _EPSG_BASE_SOUTH
    return base + zone
```