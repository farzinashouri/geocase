```python
def utm_epsg_for(lon, lat):
    is_north = lat >= 0
    hemisphere_base = 32600 if is_north else 32700
    
    zone = int((lon + 180) // 6) + 1
    if zone > 60:
        zone = 1
    
    if 56 <= lat < 64:
        if 0 <= lon < 3:
            zone = 31
        elif 3 <= lon < 12:
            zone = 32
    elif 72 <= lat < 84:
        if -6 <= lon < 9:
            zone = 31
        elif 9 <= lon < 21:
            zone = 33
        elif 21 <= lon < 33:
            zone = 35
        elif 33 <= lon < 42:
            zone = 37
    
    return hemisphere_base + zone
```