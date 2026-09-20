"""Geohash neighbour computation.

Pure standard library.  Importing this module has no side effects.
"""

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _bit_counts(precision):
    """Number of longitude and latitude bits used by a geohash of `precision` chars."""
    total = 5 * precision
    lon_bits = (total + 1) // 2
    lat_bits = total // 2
    return lon_bits, lat_bits


def _decode_center(gh):
    """Return (lat, lon) of the centre of the cell named by `gh`."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    is_lon = True
    for ch in gh:
        try:
            val = _DECODE[ch.lower()]
        except KeyError:
            raise ValueError("invalid geohash character: %r" % (ch,))
        for mask in (16, 8, 4, 2, 1):
            bit = val & mask
            if is_lon:
                mid = (lon_lo + lon_hi) / 2
                if bit:
                    lon_lo = mid
                else:
                    lon_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if bit:
                    lat_lo = mid
                else:
                    lat_hi = mid
            is_lon = not is_lon
    return (lat_lo + lat_hi) / 2, (lon_lo + lon_hi) / 2


def _encode(lat, lon, precision):
    """Encode a point as a geohash of the given precision."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    is_lon = True
    bit = 0
    val = 0
    out = []
    while len(out) < precision:
        if is_lon:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                val = (val << 1) | 1
                lon_lo = mid
            else:
                val <<= 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                val = (val << 1) | 1
                lat_lo = mid
            else:
                val <<= 1
                lat_hi = mid
        is_lon = not is_lon
        bit += 1
        if bit == 5:
            out.append(_BASE32[val])
            bit = 0
            val = 0
    return "".join(out)


def geohash_neighbors(gh):
    """Return the geohashes of the cells surrounding `gh`, at the same precision.

    Up to eight neighbours are returned, in no particular order.  East/west
    neighbours wrap across the antimeridian; cells that would lie beyond a pole
    do not exist and are omitted, so a cell touching a pole has fewer than eight
    neighbours.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string")
    if not gh:
        raise ValueError("geohash must be non-empty")

    gh = gh.lower()
    precision = len(gh)
    lat, lon = _decode_center(gh)

    lon_bits, lat_bits = _bit_counts(precision)
    lat_step = 180.0 / (1 << lat_bits) if lat_bits else None
    lon_step = 360.0 / (1 << lon_bits)

    neighbors = []
    seen = {gh}
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            if dlat:
                if lat_step is None:
                    continue  # single latitude band: no north/south neighbours
                nlat = lat + dlat * lat_step
                if nlat >= 90.0 or nlat <= -90.0:
                    continue  # beyond the pole: no such cell
            else:
                nlat = lat
            nlon = lon + dlon * lon_step
            # wrap across the antimeridian
            nlon = ((nlon + 180.0) % 360.0) - 180.0
            code = _encode(nlat, nlon, precision)
            if code not in seen:
                seen.add(code)
                neighbors.append(code)
    return neighbors