```python
"""Compute the 8 neighboring geohash cells of a geohash, at the same precision."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _decode_bits(geohash):
    bits = []
    for char in geohash:
        value = _BASE32_INDEX[char]
        for i in (4, 3, 2, 1, 0):
            bits.append((value >> i) & 1)
    return bits


def _bits_to_int(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def _int_to_bits(value, nbits):
    return [(value >> i) & 1 for i in range(nbits - 1, -1, -1)]


def geohash_neighbors(gh):
    """Return the geohashes (same precision as `gh`) of the up-to-8 cells surrounding it.

    Longitude wraps across the antimeridian; latitude does not wrap, so a cell
    touching the north or south pole yields fewer than 8 neighbors.
    """
    gh = gh.lower()
    n = len(gh)
    if n == 0:
        return []

    bits = _decode_bits(gh)
    lon_bits = bits[0::2]
    lat_bits = bits[1::2]
    nlon = len(lon_bits)
    nlat = len(lat_bits)

    lon_int = _bits_to_int(lon_bits)
    lat_int = _bits_to_int(lat_bits)
    lon_size = 1 << nlon
    lat_size = 1 << nlat

    neighbors = []
    for dlat in (-1, 0, 1):
        new_lat = lat_int + dlat
        if new_lat < 0 or new_lat >= lat_size:
            continue
        new_lat_bits = _int_to_bits(new_lat, nlat)
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            new_lon = (lon_int + dlon) % lon_size
            new_lon_bits = _int_to_bits(new_lon, nlon)

            merged = [0] * (nlon + nlat)
            merged[0::2] = new_lon_bits
            merged[1::2] = new_lat_bits

            chars = []
            for i in range(0, len(merged), 5):
                chunk = merged[i:i + 5]
                value = 0
                for bit in chunk:
                    value = (value << 1) | bit
                chars.append(_BASE32[value])
            neighbors.append("".join(chars))

    return neighbors
```