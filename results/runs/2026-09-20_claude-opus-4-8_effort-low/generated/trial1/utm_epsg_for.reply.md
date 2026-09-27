```python
"""Compute the WGS 84 / UTM EPSG code for a WGS84 lon/lat location.

Zones follow the Military Grid Reference System, including the published
grid exceptions for southwest Norway (zone 32V) and Svalbard (band X).

Importing this module has no side effects.
"""


def utm_epsg_for(lon, lat):
    """Return the EPSG code (int) of the WGS 84 / UTM CRS for (lon, lat).

    ``lon`` and ``lat`` are WGS84 longitude and latitude in decimal degrees.
    Northern-hemisphere zones return 326xx, southern 327xx, where xx is the
    UTM zone number (with MGRS grid exceptions applied).
    """
    # Normalize longitude to [-180, 180).
    lon = (lon + 180.0) % 360.0 - 180.0

    # Base zone number, 1..60.
    zone = int((lon + 180.0) // 6.0) + 1
    if zone < 1:
        zone = 1
    elif zone > 60:
        zone = 60

    # Exception 1: southwest Norway (band V, 56 <= lat < 64).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Exception 2: Svalbard (band X, 72 <= lat < 84).
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37

    base = 32600 if lat >= 0.0 else 32700
    return base + zone
```