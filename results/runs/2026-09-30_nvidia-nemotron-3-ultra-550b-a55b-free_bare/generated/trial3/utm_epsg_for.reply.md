```python
import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code for the WGS 84 / UTM zone containing the given
    longitude/latitude (in degrees), following the Military Grid Reference
    System zone numbering including the standard Norway and Svalbard exceptions.

    EPSG codes are 326xx for the northern hemisphere (lat >= 0) and 327xx for
    the southern hemisphere (lat < 0), where xx is the UTM zone number (1-60).

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84), typically in [-180, 180].
    lat : float
        Latitude in degrees (WGS84), typically in [-80, 84] for UTM.

    Returns
    -------
    int
        The EPSG code (e.g., 32633 for zone 33 north).
    """
    # Standard UTM zone calculation (1-60)
    zone = math.floor((lon + 180) / 6) + 1
    if zone > 60:
        zone = 60
    elif zone < 1:
        zone = 1

    # Norway exception: zone 32V extends to 3°E in latitude band V (56°N–64°N)
    if 56 <= lat < 64 and 3 <= lon < 6:
        zone = 32

    # Svalbard exception: in latitude band X (72°N–84°N) zones 31,33,35,37 are
    # widened to 9° and zones 32,34,36 are omitted (for 0°E–42°E).
    if 72 <= lat < 84 and 0 <= lon < 42:
        if lon < 9:
            zone = 31
        elif lon < 21:
            zone = 33
        elif lon < 33:
            zone = 35
        else:  # lon < 42
            zone = 37

    # Northern hemisphere: 32600 + zone, Southern: 32700 + zone
    return 32600 + zone if lat >= 0 else 32700 + zone
```