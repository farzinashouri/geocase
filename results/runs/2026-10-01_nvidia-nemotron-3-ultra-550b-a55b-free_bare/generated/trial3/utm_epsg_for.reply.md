```python
import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code for the WGS 84 / UTM zone containing the given
    longitude/latitude, using the Military Grid Reference System (MGRS)
    grid zone exceptions (Norway and Svalbard).

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84). Any real value is accepted; it will be
        normalized to the range [-180, 180).
    lat : float
        Latitude in degrees (WGS84).

    Returns
    -------
    int
        EPSG code (326xx for northern hemisphere, 327xx for southern).
    """
    # Normalize longitude to [-180, 180)
    lon = (lon + 180.0) % 360.0 - 180.0

    # Standard UTM zone number (1..60)
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1

    # MGRS grid zone exceptions
    # 1) Norway: zone 32 extended to 3°E in latitude band V (56°N–64°N)
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 6.0:
        zone = 32
    # 2) Svalbard: in band X (72°N–84°N) zones 31,33,35,37 are widened to 12°
    elif 72.0 <= lat < 84.0:
        if 0.0 <= lon < 12.0:
            zone = 31
        elif 12.0 <= lon < 24.0:
            zone = 33
        elif 24.0 <= lon < 36.0:
            zone = 35
        elif 36.0 <= lon < 42.0:
            zone = 37

    # Hemisphere determines the EPSG series
    if lat >= 0.0:
        return 32600 + zone
    else:
        return 32700 + zone
```