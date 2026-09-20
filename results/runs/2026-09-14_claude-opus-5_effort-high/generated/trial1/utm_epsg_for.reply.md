```python
"""WGS 84 / UTM EPSG lookup for a geographic position.

The zone containing a point is determined the way the Military Grid
Reference System assigns grid zones, i.e. the regular 6-degree zones plus
the two published exceptions:

* Grid zone 32V is widened westward to 3 degrees East (at the expense of
  31V) so that south-western Norway falls in a single zone.
* In latitude band X (Svalbard) zones 32, 34 and 36 are not used; zones
  31, 33, 35 and 37 are widened to 9, 12, 12 and 9 degrees respectively.

The module has no import-time side effects and uses only the standard
library.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

# EPSG code bases: 326xx is WGS 84 / UTM zone xxN, 327xx is zone xxS.
_NORTH_BASE = 32600
_SOUTH_BASE = 32700

# Latitude range covered by the UTM grid zones (bands C..X).  Outside of
# this range the Universal Polar Stereographic system applies instead.
_MIN_LAT = -80.0
_MAX_LAT = 84.0

# Norway exception: latitude band V spans [56, 64) degrees North, where
# zone 32 starts at 3 degrees East instead of 6.
_BAND_V_MIN_LAT = 56.0
_BAND_V_MAX_LAT = 64.0

# Svalbard exception: latitude band X spans [72, 84] degrees North and is
# divided into the widened zones below; longitudes outside [0, 42) keep
# their regular zone.
_BAND_X_MIN_LAT = 72.0
_SVALBARD_ZONES = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0
    return wrapped - 180.0


def _zone_number(lon: float, lat: float) -> int:
    """Return the MGRS grid zone number for a normalized longitude."""
    if _BAND_V_MIN_LAT <= lat < _BAND_V_MAX_LAT and 3.0 <= lon < 12.0:
        return 32

    if lat >= _BAND_X_MIN_LAT:
        for lon_start, lon_end, zone in _SVALBARD_ZONES:
            if lon_start <= lon < lon_end:
                return zone

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Guard against floating point landing exactly on the eastern edge.
    return min(zone, 60)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing a point.

    Parameters
    ----------
    lon, lat:
        WGS 84 longitude and latitude in decimal degrees.  Longitudes are
        wrapped into [-180, 180); latitude must lie within the UTM grid
        extent of [-80, 84] degrees.

    Returns
    -------
    int
        32601..32660 for northern-hemisphere zones, 32701..32760 for
        southern-hemisphere zones.

    Raises
    ------
    ValueError
        If either coordinate is not finite, or the latitude falls outside
        the latitude range covered by the UTM grid zones.
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError("lon and lat must be finite numbers")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"latitude {lat} is outside the UTM grid zone extent "
            f"[{_MIN_LAT}, {_MAX_LAT}]; the polar regions use UPS"
        )

    lon = _normalize_longitude(lon)
    zone = _zone_number(lon, lat)
    base = _NORTH_BASE if lat >= 0.0 else _SOUTH_BASE
    return base + zone
```