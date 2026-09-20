```python
def utm_epsg_for(lon, lat):
    zone = int((lon + 180) / 6) + 1
    
    if 74 <= lat <= 84:
        if lon < 6:
            zone = 31
        elif lon < 9:
            zone = 33
        elif lon < 21:
            zone = 35
        elif lon < 33:
            zone = 37
    elif 60 <= lat < 72:
        if 3 <= lon < 12:
            zone = 32
    
    zone = max(1, min(60, zone))
    
    if lat >= 0:
        return 32600 + zone
    else:
        return 32700 + zone
```