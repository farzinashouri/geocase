```python
"""UTM zone / EPSG code lookup following MGRS grid zone conventions."""

# Norway zone 32 exception: longitudes 3-12 between latitudes 56-64 use zone 32.
_NORWAY_LAT_MIN, _NORWAY_LAT_MAX = 56.0, 64.0
_NORWAY_LON_MIN, _NORWAY_LON_MAX = 3.0, 12.0

# Svalbard exceptions: latitudes 72-84 use widened zones 31, 33, 35, 37.
_SVALBARD_LAT_MIN, _SVALBARD_LAT_MAX = 72.0, 84.0
_SVALBARD_ZONES = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)


def utm_epsg_for(lon, lat):
    """Return the EPSG code of the WGS 84 / UTM zone containing (lon, lat)."""
    lon = ((lon + 180.0) % 360.0) - 180.0

    if _SVALBARD_LAT_MIN <= lat < _SVALBARD_LAT_MAX:
        for lon_min, lon_max, zone in _SVALBARD_ZONES:
            if lon_min <= lon < lon_max:
                break
        else:
            zone = int((lon + 180.0) // 6.0) + 1
    elif _NORWAY_LAT_MIN <= lat < _NORWAY_LAT_MAX and _NORWAY_LON_MIN <= lon < _NORWAY_LON_MAX:
        zone = 32
    else:
        zone = int((lon + 180.0) // 6.0) + 1

    zone = max(1, min(60, zone))

    base = 32600 if lat >= 0 else 32700
    return base + zone
```