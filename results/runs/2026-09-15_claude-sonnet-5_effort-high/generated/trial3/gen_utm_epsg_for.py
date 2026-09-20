"""UTM zone / EPSG code lookup for WGS84 coordinates (MGRS zone rules)."""


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS for the MGRS grid zone
    containing (lon, lat).

    Applies the standard 6-degree UTM zoning, including the published
    exceptions for southwestern Norway (zone 32 extended) and Svalbard
    (zones 31, 33, 35, 37 widened to 12 degrees, 32/34/36 skipped).
    """
    lon_norm = ((lon + 180.0) % 360.0) - 180.0

    if 56.0 <= lat < 64.0 and 3.0 <= lon_norm < 12.0:
        zone = 32
    elif 72.0 <= lat < 84.0 and 0.0 <= lon_norm < 42.0:
        if lon_norm < 9.0:
            zone = 31
        elif lon_norm < 21.0:
            zone = 33
        elif lon_norm < 33.0:
            zone = 35
        else:
            zone = 37
    else:
        zone = int((lon_norm + 180.0) // 6.0) + 1
        zone = max(1, min(60, zone))

    base = 32600 if lat >= 0.0 else 32700
    return base + zone