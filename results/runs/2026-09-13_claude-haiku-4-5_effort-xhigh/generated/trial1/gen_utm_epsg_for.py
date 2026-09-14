import math

def utm_epsg_for(lon, lat):
    """
    Return the EPSG code for the UTM zone containing the given WGS84 coordinates.
    
    Uses Military Grid Reference System (MGRS) zone numbering with published grid exceptions.
    
    Args:
        lon: Longitude in degrees (-180 to 180)
        lat: Latitude in degrees (-90 to 90)
    
    Returns:
        EPSG code as an integer (326xx for northern hemisphere, 327xx for southern)
    """
    # Apply MGRS grid exceptions
    
    # Svalbard: 74°N-84°N with special wider zones for 0-42°E
    if 74 <= lat < 84 and 0 <= lon < 42:
        if lon < 9:
            zone = 31
        elif lon < 21:
            zone = 33
        elif lon < 33:
            zone = 35
        else:  # 33 <= lon < 42
            zone = 37
    # Norway: 60°N-64°N with extended zone 32
    elif 60 <= lat < 64 and 0 <= lon < 12:
        zone = 31 if lon < 3 else 32
    # Standard UTM zones
    else:
        zone = int(math.floor((lon + 180) / 6)) + 1
        if zone > 60:
            zone = 60
    
    # Return EPSG code (326xx northern, 327xx southern)
    return (32600 if lat >= 0 else 32700) + zone