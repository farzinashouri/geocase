import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code for the WGS 84 / UTM zone containing the given
    longitude and latitude, following the Military Grid Reference System
    (MGRS) grid zone numbering including the published exceptions for
    Norway and Svalbard.

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84), range [-180, 180].
    lat : float
        Latitude in degrees (WGS84), range [-90, 90].

    Returns
    -------
    int
        EPSG code (326xx for northern hemisphere, 327xx for southern).
    """
    # Helper to compute standard UTM zone number (1-60) from longitude
    def standard_zone(lon_val: float) -> int:
        if lon_val == 180.0:
            return 60
        zone = math.floor((lon_val + 180.0) / 6.0) + 1
        # Clamp just in case of floating point issues
        if zone < 1:
            return 1
        if zone > 60:
            return 60
        return zone

    # Determine hemisphere and base EPSG
    if lat >= 0:
        # Northern hemisphere: check for MGRS exceptions
        zone = standard_zone(lon)
        # Norway exception: zone 32 extended to 3°E between 56°N and 64°N
        if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
            zone = 32
        # Svalbard exceptions: zones 31, 33, 35, 37 widened between 72°N and 84°N
        elif 72.0 <= lat < 84.0:
            if 0.0 <= lon < 9.0:
                zone = 31
            elif 9.0 <= lon < 21.0:
                zone = 33
            elif 21.0 <= lon < 33.0:
                zone = 35
            elif 33.0 <= lon < 42.0:
                zone = 37
        return 32600 + zone
    else:
        # Southern hemisphere: no exceptions
        zone = standard_zone(lon)
        return 32700 + zone