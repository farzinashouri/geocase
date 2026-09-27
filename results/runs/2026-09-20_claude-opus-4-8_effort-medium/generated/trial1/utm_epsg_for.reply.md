```python
"""Compute the WGS 84 / UTM EPSG code for a WGS84 longitude/latitude.

Zones follow the Military Grid Reference System, including the published
grid exceptions for south-west Norway (zone 32V) and Svalbard (zones
31X, 33X, 35X, 37X). Northern-hemisphere codes are 326xx, southern are
327xx, with xx the two-digit UTM zone number.

Importing this module has no side effects.
"""

import math


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for (lon, lat).

    Parameters
    ----------
    lon : float
        WGS84 longitude in decimal degrees.
    lat : float
        WGS84 latitude in decimal degrees.

    Returns
    -------
    int
        326xx for the northern hemisphere, 327xx for the southern,
        where xx is the UTM zone number containing the location.
    """
    lon = float(lon)
    lat = float(lat)

    if math.isnan(lon) or math.isnan(lat):
        raise ValueError("lon and lat must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be in [-90, 90]")

    # Normalise longitude to [-180, 180).
    lon = (lon + 180.0) % 360.0 - 180.0

    # Standard zone number: 6-degree-wide zones, zone 1 starts at -180.
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if zone > 60:  # can happen exactly at lon == 180.0 after normalisation
        zone = 1

    # Exception 1: south-west Norway. Latitude band V (56 <= lat < 64),
    # longitudes 3 <= lon < 12 all fall in zone 32.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Exception 2: Svalbard. Latitude band X (72 <= lat < 84) uses only
    # the odd zones 31, 33, 35, 37 across 0..42 E.
    elif 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37

    hemisphere_base = 32600 if lat >= 0.0 else 32700
    return hemisphere_base + zone
```