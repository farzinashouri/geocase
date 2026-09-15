```python
"""Compute geohash neighbor cells via direct bit manipulation."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _decode_bits(gh):
    bits = []
    for c in gh:
        idx = _BASE32_INDEX[c]
        for i in range(4, -1, -1):
            bits.append((idx >> i) & 1)
    return bits


def _bits_to_int(bits):
    val = 0
    for b in bits:
        val = (val << 1) | b
    return val


def _int_to_bits(val, n):
    return [(val >> i) & 1 for i in range(n - 1, -1, -1)]


def _bits_to_geohash(bits):
    chars = []
    for i in range(0, len(bits), 5):
        chunk = bits[i:i + 5]
        val = 0
        for b in chunk:
            val = (val << 1) | b
        chars.append(_BASE32[val])
    return "".join(chars)


def geohash_neighbors(gh):
    """Return the geohashes (same precision) of the up-to-8 cells surrounding `gh`.

    East/west neighbours wrap across the antimeridian. Neighbours that would
    lie beyond a pole do not exist and are omitted from the result.
    """
    gh = gh.lower()
    bits = _decode_bits(gh)
    total_bits = len(bits)

    lon_bits = bits[0::2]
    lat_bits = bits[1::2]

    num_lon_bits = len(lon_bits)
    num_lat_bits = len(lat_bits)

    lon_val = _bits_to_int(lon_bits)
    lat_val = _bits_to_int(lat_bits)

    lat_size = 1 << num_lat_bits
    lon_size = 1 << num_lon_bits

    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1), (0, 1),
        (1, -1), (1, 0), (1, 1),
    ]

    results = []
    for d_lat, d_lon in directions:
        new_lat = lat_val + d_lat
        if new_lat < 0 or new_lat >= lat_size:
            continue
        new_lon = (lon_val + d_lon) % lon_size

        new_lon_bits = _int_to_bits(new_lon, num_lon_bits)
        new_lat_bits = _int_to_bits(new_lat, num_lat_bits)

        interleaved = []
        for i in range(num_lon_bits):
            interleaved.append(new_lon_bits[i])
            if i < num_lat_bits:
                interleaved.append(new_lat_bits[i])

        results.append(_bits_to_geohash(interleaved[:total_bits]))

    return results
```