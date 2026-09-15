```python
"""Compute the geohash neighbours of a geohash cell using exact integer bit math."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _char_to_bits(c):
    v = _BASE32_INDEX[c]
    return [(v >> (4 - i)) & 1 for i in range(5)]


def _bits_to_char(bits5):
    v = 0
    for b in bits5:
        v = (v << 1) | b
    return _BASE32[v]


def _bits_to_int(bits):
    v = 0
    for b in bits:
        v = (v << 1) | b
    return v


def _int_to_bits(v, n):
    return [(v >> (n - 1 - i)) & 1 for i in range(n)]


def geohash_neighbors(gh):
    """Return the geohashes of the up-to-8 cells surrounding `gh`, same precision.

    Longitude wraps across the antimeridian; latitude does not wrap, so a
    cell touching a pole yields fewer than 8 neighbours.
    """
    gh = gh.lower()
    bits = []
    for c in gh:
        bits.extend(_char_to_bits(c))
    total = len(bits)

    # Geohash bits alternate starting with longitude, so even positions are
    # longitude bits and odd positions are latitude bits.
    lon_bits = bits[0::2]
    lat_bits = bits[1::2]
    lon_n = len(lon_bits)
    lat_n = len(lat_bits)

    lon_val = _bits_to_int(lon_bits)
    lat_val = _bits_to_int(lat_bits)

    neighbors = []
    for dlon in (-1, 0, 1):
        for dlat in (-1, 0, 1):
            if dlon == 0 and dlat == 0:
                continue

            new_lat = lat_val + dlat
            if lat_n == 0 or new_lat < 0 or new_lat >= (1 << lat_n):
                continue  # beyond a pole: no such cell

            new_lon = (lon_val + dlon) % (1 << lon_n) if lon_n else 0

            new_lon_bits = _int_to_bits(new_lon, lon_n)
            new_lat_bits = _int_to_bits(new_lat, lat_n)

            combined = [0] * total
            combined[0::2] = new_lon_bits
            combined[1::2] = new_lat_bits

            chars = [
                _bits_to_char(combined[i:i + 5])
                for i in range(0, total, 5)
            ]
            neighbors.append("".join(chars))

    return neighbors
```