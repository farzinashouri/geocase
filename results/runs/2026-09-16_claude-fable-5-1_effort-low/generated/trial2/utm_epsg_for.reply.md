```python
"""WGS 84 / UTM EPSG code lookup using Military Grid Reference System zones.

Grid zone numbering follows the MGRS convention, including the two published
exceptions to the regular 6-degree longitude bands:

* Norway: latitude band V (56N-64N), longitudes 3E-12E belong to zone 32.
* Svalbard: latitude band X (72N-84N), zones 32, 34 and 36 are unused;
  0E-9E -> 31, 9E-21E -> 33, 21E-33E -> 35, 33E-42E -> 37.

EPSG codes are 326xx (north) / 327xx (south) with xx the zone number.
"""

from __future__ import annotations

__all__ = ["utm_epsg_for"]

_MIN_LAT = -80.0
_MAX_LAT = 84.0


def utm_zone_for(lon: float, lat: float) -> int:
    """Return the MGRS/UTM grid zone number (1-60) for a WGS84 lon/lat."""
    lon = float(lon)
    lat = float(lat)
    if lon != lon or lat != lat:
        raise ValueError("longitude and latitude must not be NaN")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude {lon} outside [-180, 180]")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"latitude {lat} outside UTM coverage [{_MIN_LAT}, {_MAX_LAT}]; "
            "polar regions use UPS, not UTM"
        )

    # Regular 6-degree bands; +180 maps exactly to zone 60.
    zone = int((lon + 180.0) // 6.0) + 1
    if zone > 60:
        zone = 60

    # Norway exception (band V).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Svalbard exception (band X, 72N up to and including 84N).
    if 72.0 <= lat <= _MAX_LAT:
        if 0.0 <= lon < 9.0:
            return 31
        if 9.0 <= lon < 21.0:
            return 33
        if 21.0 <= lon < 33.0:
            return 35
        if 33.0 <= lon < 42.0:
            return 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of WGS 84 / UTM for the MGRS grid zone at (lon, lat).

    Northern hemisphere (lat >= 0) yields 326xx, southern yields 327xx.
    """
    zone = utm_zone_for(lon, lat)
    base = 32600 if float(lat) >= 0.0 else 32700
    return base + zone
```