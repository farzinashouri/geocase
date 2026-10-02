```python
def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code for the WGS 84 / UTM zone containing the given
    longitude and latitude (in degrees), following the Military Grid
    Reference System (MGRS) zone numbering including the published
    exceptions for Norway and Svalbard.

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS84), range [-180, 180].
    lat : float
        Latitude in degrees (WGS84), range [-90, 90].

    Returns
    -------
    int
        EPSG code (32601-32660 for northern hemisphere, 32701-32760 for southern).
    """
    # Standard UTM zone calculation (1-60)
    if lon == 180:
        zone = 60
    else:
        zone = int((lon + 180) / 6) + 1

    # MGRS exceptions (northern hemisphere only)
    if lat >= 0:
        # Norway: zone 32 extended west to 3°E between 56°N and 64°N
        if 56 <= lat < 64 and 3 <= lon < 6:
            zone = 32
        # Svalbard: special zones between 72°N and 84°N
        elif 72 <= lat < 84:
            if 0 <= lon < 9:
                zone = 31
            elif 9 <= lon < 21:
                zone = 33
            elif 21 <= lon < 33:
                zone = 35
            elif 33 <= lon < 42:
                zone = 37

    # Clamp zone to valid range (should already be 1-60)
    zone = max(1, min(60, zone))

    # EPSG codes: 326xx for north, 327xx for south
    return 32600 + zone if lat >= 0 else 32700 + zone
```