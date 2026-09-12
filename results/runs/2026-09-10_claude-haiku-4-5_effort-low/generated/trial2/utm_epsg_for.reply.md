```python
def utm_epsg_for(lon, lat):
    import math
    
    # Normalize longitude to [-180, 180)
    lon = ((lon + 180) % 360) - 180
    
    # Basic zone calculation
    zone = math.floor((lon + 180) / 6) + 1
    
    # Handle MGRS grid exceptions
    
    # Svalbard exceptions (72°N to 84°N, 0°E to 42°E)
    if 72 <= lat <= 84 and 0 <= lon < 42:
        if lon < 9:
            zone = 31
        elif lon < 21:
            zone = 33
        elif lon < 33:
            zone = 35
        else:  # 33 <= lon < 42
            zone = 37
    # Norway exceptions (56°N to 64°N, 0°E to 36°E)
    elif 56 <= lat < 64 and 0 <= lon < 36:
        if lon < 3:
            zone = 31
        elif lon < 12:
            zone = 32
    
    # Ensure zone is in valid range [1, 60]
    zone = max(1, min(60, zone))
    
    # Return EPSG code
    if lat >= 0:
        return 32600 + zone
    else:
        return 32700 + zone
```