"""Compute the EPSG code of the WGS 84 / UTM CRS for a longitude/latitude pair."""


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM zone containing (lon, lat).

    Zone numbering follows the Military Grid Reference System, including the
    published exceptions for southwest Norway (zone 32 extended) and Svalbard
    (zones 31, 33, 35, 37 extended; 32, 34, 36 eliminated).
    """
    # Normalize longitude into [-180, 180).
    lon = ((lon + 180.0) % 360.0) - 180.0

    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        # Southwest Norway exception: zone 32 extended west to 3E.
        zone = 32
    elif 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        # Svalbard exception: zones 31/33/35/37 widened to 12 degrees each,
        # replacing 31-37, with 32/34/36 eliminated.
        if lon < 9.0:
            zone = 31
        elif lon < 21.0:
            zone = 33
        elif lon < 33.0:
            zone = 35
        else:
            zone = 37
    else:
        zone = int((lon + 180.0) // 6.0) + 1
        zone = max(1, min(60, zone))

    hemisphere_prefix = 326 if lat >= 0 else 327
    return hemisphere_prefix * 100 + zone