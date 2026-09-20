"""UTM/MGRS grid zone EPSG code lookup for WGS 84 coordinates."""


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM zone containing (lon, lat).

    Zone assignment follows the Military Grid Reference System, including
    the published Norway and Svalbard grid zone exceptions.
    """
    lon = ((lon + 180.0) % 360.0) - 180.0

    if 72.0 <= lat <= 84.0:
        # Svalbard exception (latitude band X): zones 32, 34, 36 are
        # eliminated and their neighbours widened to compensate.
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37
        else:
            zone = int((lon + 180.0) // 6.0) + 1
    elif 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        # Norway exception (latitude band V): zone 32 is widened to cover
        # southwestern Norway, shrinking zone 31 to the sea west of it.
        zone = 32
    else:
        zone = int((lon + 180.0) // 6.0) + 1

    zone = max(1, min(60, zone))
    hemisphere = 326 if lat >= 0 else 327
    return hemisphere * 100 + zone