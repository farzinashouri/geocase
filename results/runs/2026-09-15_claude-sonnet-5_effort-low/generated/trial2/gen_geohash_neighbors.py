"""Compute the 8 geohash neighbors of a given geohash cell."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _decode(gh):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    is_lon = True
    for ch in gh:
        idx = _BASE32.index(ch)
        for bit in range(4, -1, -1):
            bitval = (idx >> bit) & 1
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bitval:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bitval:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_lon = not is_lon
    lat = (lat_range[0] + lat_range[1]) / 2
    lon = (lon_range[0] + lon_range[1]) / 2
    return lat, lon


def _encode(lat, lon, precision):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    geohash = []
    bit = 0
    ch = 0
    is_lon = True
    while len(geohash) < precision:
        if is_lon:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                ch = (ch << 1) | 1
                lon_range[0] = mid
            else:
                ch = ch << 1
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch = (ch << 1) | 1
                lat_range[0] = mid
            else:
                ch = ch << 1
                lat_range[1] = mid
        is_lon = not is_lon
        bit += 1
        if bit == 5:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def _cell_bounds(gh):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    is_lon = True
    for ch in gh:
        idx = _BASE32.index(ch)
        for bit in range(4, -1, -1):
            bitval = (idx >> bit) & 1
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bitval:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bitval:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_lon = not is_lon
    return lat_range, lon_range


def geohash_neighbors(gh):
    """Return the geohashes of the 8 cells surrounding `gh`, at the same precision.

    Longitude wraps across the antimeridian; cells beyond the poles are omitted.
    """
    precision = len(gh)
    lat_range, lon_range = _cell_bounds(gh)
    lat_span = lat_range[1] - lat_range[0]
    lon_span = lon_range[1] - lon_range[0]
    lat_center = (lat_range[0] + lat_range[1]) / 2
    lon_center = (lon_range[0] + lon_range[1]) / 2

    neighbors = set()
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            n_lat = lat_center + dlat * lat_span
            if n_lat < -90.0 or n_lat > 90.0:
                continue
            n_lon = lon_center + dlon * lon_span
            # wrap longitude across the antimeridian
            n_lon = ((n_lon + 180.0) % 360.0) - 180.0
            neighbors.add(_encode(n_lat, n_lon, precision))

    return list(neighbors)