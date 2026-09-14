```python
def utm_epsg_for(lon, lat):
    """Return the EPSG code for the UTM zone containing the WGS84 coordinates, using MGRS zone numbering with published grid exceptions."""
    
    # Normalize longitude to [-180, 180)
    lon = ((lon + 180) % 360) - 180
    
    # Standard UTM zone calculation: 60 zones, 6° wide each
    zone = int((lon + 180) / 6) + 1
    
    # Norway exception: zone 32 extends westward from 3°E to 12°E (56°N to 64°N)
    if 3.0 <= lon < 12.0 and 56.0 <= lat <= 64.0:
        zone = 32
    
    # Svalbard exceptions: modified zones for high latitudes (> 72°N)
    elif lat > 72.0 and 0.0 <= lon < 42.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37
    
    # Return EPSG code: 326xx for northern hemisphere, 327xx for southern
    return 32600 + zone if lat >= 0 else 32700 + zone
```