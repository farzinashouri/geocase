import math

def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code of the UTM coordinate reference system that is
    appropriate for the given WGS84 longitude and latitude.

    Parameters
    ----------
    lon : float
        Longitude in degrees, must be in the range [-180, 180].
    lat : float
        Latitude in degrees, must be in the range [-90, 90].

    Returns
    -------
    int
        EPSG code of the UTM zone (326xx for the Northern hemisphere,
        327xx for the Southern hemisphere).

    Raises
    ------
    ValueError
        If the longitude or latitude is outside the valid range.
    """
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError("Latitude must be between -90 and 90 degrees.")

    # Compute UTM zone number (1-60). 180° longitude belongs to zone 60.
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if lon == 180.0:
        zone = 60

    # EPSG codes: 326xx for northern hemisphere, 327xx for southern.
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return epsg