def utm_epsg_for(lon, lat):
    zone = int((lon + 180) / 6) + 1
    if zone > 60:
        zone = 1
    
    # MGRS exceptions: Norway (56°N to 64°N)
    if 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32 if lon < 9 else 31
    
    # MGRS exceptions: Svalbard (72°N to 84°N)
    if 72 <= lat < 84:
        if lon < 9:
            zone = 31
        elif lon < 21:
            zone = 33
        elif lon < 33:
            zone = 35
        elif lon < 42:
            zone = 37
    
    return (32600 if lat >= 0 else 32700) + zone