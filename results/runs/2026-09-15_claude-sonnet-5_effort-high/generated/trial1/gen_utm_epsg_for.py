def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the MGRS grid zone
    containing (lon, lat), including the Norway/Svalbard exceptions."""
    lon = ((lon + 180.0) % 360.0) - 180.0

    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32
    elif 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37
        else:
            zone = int((lon + 180.0) / 6.0) + 1
    else:
        zone = int((lon + 180.0) / 6.0) + 1

    zone = max(1, min(60, zone))

    base = 32600 if lat >= 0 else 32700
    return base + zone