```python
def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM zone containing (lon, lat).

    Zone numbering follows the Military Grid Reference System, including the
    published grid exceptions around Norway and Svalbard.
    """
    lon = ((lon + 180.0) % 360.0) - 180.0

    zone = int((lon + 180.0) // 6) + 1

    # Norway exception: zone 32 extended to cover 3-12E between 56 and 64N.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Svalbard exceptions: zones 31, 33, 35, 37 extended; 32, 34, 36 unused.
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37

    zone = max(1, min(60, zone))

    base = 32600 if lat >= 0 else 32700
    return base + zone
```