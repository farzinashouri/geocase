def utm_epsg_for(lon, lat):
    """Return the EPSG code for the WGS84/UTM zone containing (lon, lat)."""
    lon = ((lon + 180) % 360) - 180
    is_north = lat >= 0
    zone = int((lon + 180) / 6) + 1
    
    # MGRS exceptions
    if 72 <= lat < 84:  # Svalbard
        if 0 <= lon < 9:
            zone = 31
        elif 9 <= lon < 21:
            zone = 33
        elif 21 <= lon < 33:
            zone = 35
        elif 33 <= lon <= 42:
            zone = 37
    elif 56 <= lat < 64 and 3 <= lon < 12:  # Norway
        zone = 31
    
    zone = max(1, min(60, zone))
    return (32600 if is_north else 32700) + zone