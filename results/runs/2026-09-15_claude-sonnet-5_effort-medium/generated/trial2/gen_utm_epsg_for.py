def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code for the WGS 84 / UTM zone containing (lon, lat).

    Zone numbering follows the Military Grid Reference System (MGRS),
    including the Norway/Svalbard grid exceptions.
    """
    lon = ((lon + 180.0) % 360.0) - 180.0

    zone = int((lon + 180.0) / 6.0) + 1
    if zone > 60:
        zone = 60
    if zone < 1:
        zone = 1

    # Norway exception: zone 32 extends to cover 3E-12E for 56N-64N.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Svalbard exceptions: zones 31,33,35,37 widened, 32/34/36 dropped, for 72N-84N.
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37

    base = 32600 if lat >= 0 else 32700
    return base + zone