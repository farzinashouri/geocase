```python
"""Compute the 8 geohash neighbors of a geohash cell."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _decode(geohash):
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    is_lon = True
    for c in geohash:
        cd = _BASE32_INDEX[c]
        for mask in (16, 8, 4, 2, 1):
            if is_lon:
                mid = (lon_interval[0] + lon_interval[1]) / 2
                if cd & mask:
                    lon_interval[0] = mid
                else:
                    lon_interval[1] = mid
            else:
                mid = (lat_interval[0] + lat_interval[1]) / 2
                if cd & mask:
                    lat_interval[0] = mid
                else:
                    lat_interval[1] = mid
            is_lon = not is_lon
    lat = (lat_interval[0] + lat_interval[1]) / 2
    lon = (lon_interval[0] + lon_interval[1]) / 2
    lat_err = (lat_interval[1] - lat_interval[0]) / 2
    lon_err = (lon_interval[1] - lon_interval[0]) / 2
    return lat, lon, lat_err, lon_err


def _encode(lat, lon, precision):
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    geohash = []
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon >= mid:
                ch |= 1 << (4 - bit)
                lon_interval[0] = mid
            else:
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat >= mid:
                ch |= 1 << (4 - bit)
                lat_interval[0] = mid
            else:
                lat_interval[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def geohash_neighbors(gh):
    """Return the geohashes (same precision as `gh`) of the up-to-8 cells
    surrounding `gh`. Longitude wraps across the antimeridian; neighbors
    that would lie beyond a pole are omitted."""
    precision = len(gh)
    lat, lon, lat_err, lon_err = _decode(gh)
    lat_step = lat_err * 2
    lon_step = lon_err * 2

    pole_eps = 1e-9
    neighbors = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            new_lat = lat + dlat * lat_step
            if new_lat > 90 + pole_eps or new_lat < -90 - pole_eps:
                continue
            new_lat = max(-90.0, min(90.0, new_lat))
            new_lon = lon + dlon * lon_step
            new_lon = ((new_lon + 180.0) % 360.0) - 180.0
            neighbors.append(_encode(new_lat, new_lon, precision))
    return neighbors
```