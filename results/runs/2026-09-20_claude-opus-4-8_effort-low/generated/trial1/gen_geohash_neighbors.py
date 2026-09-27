"""Compute the geohash neighbours of a geohash cell.

Given a geohash string, ``geohash_neighbors`` returns the geohashes at the
same precision for the up-to-eight cells surrounding it.  East/west
neighbours wrap across the antimeridian; neighbours that would lie beyond
the poles do not exist and are omitted.
"""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}


def _decode_bbox(gh):
    """Return (lat_min, lat_max, lon_min, lon_max) for a geohash cell."""
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True
    for ch in gh:
        try:
            cd = _DECODE_MAP[ch]
        except KeyError:
            raise ValueError("invalid geohash character: %r" % ch)
        for bit in range(4, -1, -1):
            mask = 1 << bit
            if is_lon:
                mid = (lon_min + lon_max) / 2.0
                if cd & mask:
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2.0
                if cd & mask:
                    lat_min = mid
                else:
                    lat_max = mid
            is_lon = not is_lon
    return lat_min, lat_max, lon_min, lon_max


def _encode(lat, lon, precision):
    """Encode a lat/lon point to a geohash of the given precision."""
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True
    ch = 0
    bit = 0
    gh = []
    while len(gh) < precision:
        if is_lon:
            mid = (lon_min + lon_max) / 2.0
            if lon >= mid:
                ch = (ch << 1) | 1
                lon_min = mid
            else:
                ch = ch << 1
                lon_max = mid
        else:
            mid = (lat_min + lat_max) / 2.0
            if lat >= mid:
                ch = (ch << 1) | 1
                lat_min = mid
            else:
                ch = ch << 1
                lat_max = mid
        is_lon = not is_lon
        bit += 1
        if bit == 5:
            gh.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(gh)


def geohash_neighbors(gh):
    """Return the geohashes of the (up to 8) cells surrounding ``gh``.

    The result has the same precision as ``gh`` and is in no particular
    order.  East/west neighbours wrap across the antimeridian; cells beyond
    the poles are omitted, so a cell touching a pole yields fewer than 8
    neighbours.
    """
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    precision = len(gh)
    lat_min, lat_max, lon_min, lon_max = _decode_bbox(gh)
    lat_c = (lat_min + lat_max) / 2.0
    lon_c = (lon_min + lon_max) / 2.0
    lat_h = lat_max - lat_min
    lon_w = lon_max - lon_min

    neighbours = []
    seen = set()
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue

            nlat = lat_c + dlat * lat_h
            # A neighbour whose centre is beyond a pole does not exist.
            if nlat > 90.0 or nlat < -90.0:
                continue

            nlon = lon_c + dlon * lon_w
            # Wrap longitude across the antimeridian into [-180, 180).
            nlon = ((nlon + 180.0) % 360.0) - 180.0

            code = _encode(nlat, nlon, precision)
            if code != gh and code not in seen:
                seen.add(code)
                neighbours.append(code)

    return neighbours