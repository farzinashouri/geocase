```python
import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code for the WGS 84 / UTM zone containing the given
    longitude and latitude (in degrees), following the Military Grid
    Reference System (MGRS) zone numbering including the published
    exceptions for Norway and Svalbard.

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84). Expected range [-180, 180].
    lat : float
        Latitude in degrees (WGS84). Expected range [-80, 84] for UTM.

    Returns
    -------
    int
        EPSG code (326xx for northern hemisphere, 327xx for southern).
    """
    # Normalize longitude to [-180, 180] preserving the sign of 180°
    original_lon = lon
    lon = lon % 360
    if lon > 180:
        lon -= 360
    if lon == 180 and original_lon < 0:
        lon = -180

    # Standard UTM zone calculation (1-60)
    zone = int(math.floor((lon + 180) / 6)) + 1
    if zone > 60:
        zone = 60
    if zone < 1:
        zone = 1

    # MGRS grid zone exceptions
    # Norway exception: zone 32 extended to 3°E–12°E between 56°N–64°N
    if 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32
    # Svalbard exceptions: zones 31, 33, 35, 37 between 72°N–84°N
    elif 72 <= lat < 84:
        if 0 <= lon < 9:
            zone = 31
        elif 9 <= lon < 21:
            zone = 33
        elif 21 <= lon < 33:
            zone = 35
        elif 33 <= lon < 42:
            zone = 37

    # Northern hemisphere: EPSG 326xx, Southern: 327xx
    if lat >= 0:
        return 32600 + zone
    else:
        return 32700 + zone
```