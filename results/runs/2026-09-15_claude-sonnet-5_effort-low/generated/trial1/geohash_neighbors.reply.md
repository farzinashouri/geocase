```python
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _decode(gh):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    even = True
    for c in gh:
        idx = _BASE32.index(c)
        for shift in (16, 8, 4, 2, 1):
            bit = 1 if idx & shift else 0
            if even:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bit:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bit:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            even = not even
    lat = (lat_range[0] + lat_range[1]) / 2
    lon = (lon_range[0] + lon_range[1]) / 2
    lat_err = (lat_range[1] - lat_range[0]) / 2
    lon_err = (lon_range[1] - lon_range[0]) / 2
    return lat, lon, lat_err, lon_err


def _encode(lat, lon, precision):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    geohash = []
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                ch |= (16 >> bit)
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch |= (16 >> bit)
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def geohash_neighbors(gh):
    lat, lon, lat_err, lon_err = _decode(gh)
    precision = len(gh)

    cell_lat_size = lat_err * 2
    cell_lon_size = lon_err * 2

    neighbors = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            n_lat = lat + dlat * cell_lat_size
            if n_lat > 90 or n_lat < -90:
                continue
            n_lon = lon + dlon * cell_lon_size
            n_lon = ((n_lon + 180) % 360) - 180
            neighbors.append(_encode(n_lat, n_lon, precision))

    return neighbors
```