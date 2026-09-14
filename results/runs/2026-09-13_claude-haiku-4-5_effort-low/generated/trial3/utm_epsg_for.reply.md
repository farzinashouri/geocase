```python
def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code for the UTM zone containing the given WGS84 coordinate."""
    is_north = lat >= 0
    
    # MGRS exceptions: Norway (56°N - 64°N) and Svalbard (72°N - 84°N)
    if 56 <= lat < 64:  # Norway
        if 0 <= lon < 3:
            zone = 31
        elif 3 <= lon < 12:
            zone = 32
        else:
            zone = int((lon + 180) // 6) + 1
    elif 72 <= lat < 84:  # Svalbard
        if 0 <= lon < 9:
            zone = 31
        elif 9 <= lon < 21:
            zone = 33
        elif 21 <= lon < 33:
            zone = 35
        elif 33 <= lon < 42:
            zone = 37
        else:
            zone = int((lon + 180) // 6) + 1
    else:  # Standard UTM
        zone = int((lon + 180) // 6) + 1
    
    zone = max(1, min(60, zone))
    epsg_base = 32600 if is_north else 32700
    return epsg_base + zone
```