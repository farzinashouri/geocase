```python
import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code of the UTM zone for the given WGS84 longitude and latitude.

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84), expected in the range [-180, 180].
    lat : float
        Latitude in degrees (WGS84), expected in the range [-90, 90].

    Returns
    -------
    int
        EPSG code of the appropriate UTM coordinate reference system.
        Northern hemisphere zones: 32601–32660.
        Southern hemisphere zones: 32701–32760.
    """
    # Compute UTM zone number (1–60)
    # Longitude 180° belongs to zone 60, not 61.
    zone = math.floor((lon + 180.0) / 6.0) + 1
    if zone == 61:
        zone = 60

    # Determine hemisphere
    if lat >= 0:
        # Northern hemisphere: EPSG 32600 + zone
        return 32600 + zone
    else:
        # Southern hemisphere: EPSG 32700 + zone
        return 32700 + zone
```