```python
import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code for the WGS 84 / UTM zone containing the given
    longitude and latitude (in degrees), following the Military Grid
    Reference System (MGRS) zone numbering including the standard exceptions.

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84). Any value is accepted; it will be
        normalized to the range [-180, 180).
    lat : float
        Latitude in degrees (WGS84).

    Returns
    -------
    int
        EPSG code (32601-32660 for northern hemisphere, 32701-32760 for
        southern hemisphere).
    """
    # Normalize longitude to [-180, 180)
    lon = (lon + 180.0) % 360.0 - 180.0

    # Standard UTM zone number (1-60)
    zone = int((lon + 180.0) // 6.0) + 1

    # Northern hemisphere exceptions (MGRS)
    if lat >= 0.0:
        # Norway exception: zone 32 extended to 3°E in band V (56°N–64°N)
        if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
            zone = 32
        # Svalbard exception: zones 31,33,35,37 widened to 12° in band X (72°N–84°N)
        elif 72.0 <= lat < 84.0:
            if 0.0 <= lon < 12.0:
                zone = 31
            elif 12.0 <= lon < 24.0:
                zone = 33
            elif 24.0 <= lon < 36.0:
                zone = 35
            elif 36.0 <= lon < 48.0:
                zone = 37

    # EPSG codes: 326xx for north, 327xx for south
    if lat >= 0.0:
        return 32600 + zone
    else:
        return 32700 + zone
```