```python
"""Geohash neighbour computation.

Pure standard-library implementation; importing has no side effects.
"""

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode_bbox(gh):
    """Return (lat, lon, lat_err, lon_err) for a geohash cell."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    is_lon = True
    for ch in gh:
        try:
            cd = _DECODE[ch]
        except KeyError:
            raise ValueError("invalid geohash character: %r" % ch)
        for mask in (16, 8, 4, 2, 1):
            if is_lon:
                mid = (lon_lo + lon_hi) / 2
                if cd & mask:
                    lon_lo = mid
                else:
                    lon_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if cd & mask:
                    lat_lo = mid
                else:
                    lat_hi = mid
            is_lon = not is_lon
    lat = (lat_lo + lat_hi) / 2
    lon = (lon_lo + lon_hi) / 2
    return lat, lon, (lat_hi - lat_lo) / 2, (lon_hi - lon_lo) / 2


def _encode(lat, lon, precision):
    """Encode a lat/lon point to a geohash of the given precision."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    is_lon = True
    bit = 0
    cd = 0
    out = []
    while len(out) < precision:
        if is_lon:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                cd = (cd << 1) | 1
                lon_lo = mid
            else:
                cd = cd << 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                cd = (cd << 1) | 1
                lat_lo = mid
            else:
                cd = cd << 1
                lat_hi = mid
        is_lon = not is_lon
        bit += 1
        if bit == 5:
            out.append(_BASE32[cd])
            bit = 0
            cd = 0
    return "".join(out)


def geohash_neighbors(gh):
    """Return the geohashes of the 8 cells surrounding ``gh``.

    Neighbours are at the same precision as ``gh`` and returned in any order.
    East/west neighbours wrap across the antimeridian. Cells beyond the poles
    do not exist and are omitted, so a cell touching a pole has fewer than 8
    neighbours.
    """
    if not isinstance(gh, str) or gh == "":
        raise ValueError("geohash must be a non-empty string")
    gh = gh.lower()
    precision = len(gh)
    lat, lon, lat_err, lon_err = _decode_bbox(gh)

    neighbors = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            n_lat = lat + dlat * 2 * lat_err
            if n_lat > 90.0 or n_lat < -90.0:
                # Beyond a pole: no such cell.
                continue
            n_lon = lon + dlon * 2 * lon_err
            # Wrap longitude across the antimeridian into [-180, 180).
            n_lon = ((n_lon + 180.0) % 360.0) - 180.0
            neighbors.append(_encode(n_lat, n_lon, precision))
    return neighbors
```