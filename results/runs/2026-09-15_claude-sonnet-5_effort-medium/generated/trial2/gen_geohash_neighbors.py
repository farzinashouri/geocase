"""Compute the 8 neighboring geohash cells for a given geohash string."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _decode_bounds(gh):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    even_bit = True
    for c in gh:
        idx = _BASE32_INDEX[c]
        for shift in range(4, -1, -1):
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
    return lat_range, lon_range


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
                ch |= 1 << (4 - bit)
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch |= 1 << (4 - bit)
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
    """Return the geohashes (same precision) of the up-to-8 cells surrounding gh."""
    precision = len(gh)
    lat_range, lon_range = _decode_bounds(gh)
    lat_err = lat_range[1] - lat_range[0]
    lon_err = lon_range[1] - lon_range[0]
    center_lat = (lat_range[0] + lat_range[1]) / 2
    center_lon = (lon_range[0] + lon_range[1]) / 2

    neighbors = []
    seen = set()
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            n_lat = center_lat + dlat * lat_err
            if n_lat > 90 or n_lat < -90:
                continue
            n_lat = max(-90.0, min(90.0, n_lat))
            n_lon = center_lon + dlon * lon_err
            n_lon = (n_lon + 180.0) % 360.0 - 180.0
            neighbor_gh = _encode(n_lat, n_lon, precision)
            if neighbor_gh != gh and neighbor_gh not in seen:
                seen.add(neighbor_gh)
                neighbors.append(neighbor_gh)
    return neighbors