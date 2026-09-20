_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _decode(gh):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    even_bit = True
    for ch in gh:
        idx = _BASE32_INDEX[ch]
        for shift in (4, 3, 2, 1, 0):
            bit = (idx >> shift) & 1
            if even_bit:
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
            even_bit = not even_bit
    lat = (lat_range[0] + lat_range[1]) / 2
    lon = (lon_range[0] + lon_range[1]) / 2
    return lat, lon, lat_range, lon_range


def _encode(lat, lon, precision):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    geohash = []
    even_bit = True
    bit = 0
    ch = 0
    while len(geohash) < precision:
        if even_bit:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                ch |= (1 << (4 - bit))
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch |= (1 << (4 - bit))
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        even_bit = not even_bit
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def geohash_neighbors(gh):
    precision = len(gh)
    lat, lon, lat_range, lon_range = _decode(gh)
    lat_err = lat_range[1] - lat_range[0]
    lon_err = lon_range[1] - lon_range[0]

    neighbors = []
    for dlat_steps in (-1, 0, 1):
        for dlon_steps in (-1, 0, 1):
            if dlat_steps == 0 and dlon_steps == 0:
                continue
            n_lat = lat + dlat_steps * lat_err
            if n_lat > 90.0 or n_lat < -90.0:
                continue
            n_lon = lon + dlon_steps * lon_err
            if n_lon > 180.0:
                n_lon -= 360.0
            elif n_lon < -180.0:
                n_lon += 360.0
            neighbors.append(_encode(n_lat, n_lon, precision))

    return neighbors