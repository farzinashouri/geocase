def utm_epsg_for(lon, lat):
    """
    Returns the EPSG code for the WGS84/UTM zone containing the given point.
    Uses MGRS grid zone exceptions for Svalbard and Norway.
    
    Args:
        lon: Longitude in degrees [-180, 180]
        lat: Latitude in degrees [-90, 90]
    
    Returns:
        EPSG code as an int (326xx for N hemisphere, 327xx for S hemisphere)
    """
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError(f"Invalid coordinates: lon={lon}, lat={lat}")
    
    # Svalbard exception (74°N to 84°N): special wide zones
    if 74 <= lat < 84:
        if lon < 9:
            zone = 31
        elif lon < 21:
            zone = 33
        elif lon < 33:
            zone = 35
        else:
            zone = 37
    # Norway exception (56°N to 64°N, 3°E to 12°E): zone 32 extends westward
    elif 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32
    # Standard UTM zones
    else:
        zone = int((lon + 180) / 6) + 1
        if zone > 60:
            zone = 60
        if zone < 1:
            zone = 1
    
    # EPSG code: 326xx for N hemisphere, 327xx for S hemisphere
    return 32600 + zone if lat >= 0 else 32700 + zone