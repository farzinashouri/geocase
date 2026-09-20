"""Compute the 8 geohash neighbors of a geohash cell.

Neighbors are found by re-deriving each adjacent cell's center point
(the original center shifted by one cell-width in latitude and/or
longitude) and re-encoding that point at the same precision. Longitude
shifts wrap across the antimeridian; latitude shifts that would cross
a pole are dropped, since no cell exists there.
"""

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(BASE32)}
_BITS = (16, 8, 4, 2, 1)


def _decode_exactly(geohash):
    lat_interval = (-90.0, 90.0)
    lon_interval = (-180.0, 180.0)
    even = True
    for c in geohash.lower():
        try:
            cd = _BASE32_INDEX[c]
        except KeyError:
            raise ValueError(f"invalid geohash character: {c!r}") from None
        for mask in _BITS:
            if even:
                mid = (lon_interval[0] + lon_interval[1]) / 2
                if cd & mask:
                    lon_interval = (mid, lon_interval[1])
                else:
                    lon_interval = (lon_interval[0], mid)
            else:
                mid = (lat_interval[0] + lat_interval[1]) / 2
                if cd & mask:
                    lat_interval = (mid, lat_interval[1])
                else:
                    lat_interval = (lat_interval[0], mid)
            even = not even

    lat = (lat_interval[0] + lat_interval[1]) / 2
    lon = (lon_interval[0] + lon_interval[1]) / 2
    lat_err = (lat_interval[1] - lat_interval[0]) / 2
    lon_err = (lon_interval[1] - lon_interval[0]) / 2
    return lat, lon, lat_err, lon_err


def _encode(lat, lon, precision):
    lat_interval = (-90.0, 90.0)
    lon_interval = (-180.0, 180.0)
    chars = []
    bit = 0
    ch = 0
    even = True
    while len(chars) < precision:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon > mid:
                ch |= _BITS[bit]
                lon_interval = (mid, lon_interval[1])
            else:
                lon_interval = (lon_interval[0], mid)
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat > mid:
                ch |= _BITS[bit]
                lat_interval = (mid, lat_interval[1])
            else:
                lat_interval = (lat_interval[0], mid)
        even = not even

        if bit < 4:
            bit += 1
        else:
            chars.append(BASE32[ch])
            bit = 0
            ch = 0

    return "".join(chars)


def geohash_neighbors(gh):
    """Return the geohashes (same precision as `gh`) of the up to 8 cells
    surrounding `gh`. East/west neighbors wrap across the antimeridian;
    neighbors that would fall beyond a pole are omitted.
    """
    precision = len(gh)
    lat, lon, lat_err, lon_err = _decode_exactly(gh)

    neighbors = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue

            new_lat = lat + dlat * 2 * lat_err
            if new_lat > 90 or new_lat < -90:
                continue

            new_lon = lon + dlon * 2 * lon_err
            new_lon = ((new_lon + 180) % 360) - 180

            neighbors.append(_encode(new_lat, new_lon, precision))

    return neighbors