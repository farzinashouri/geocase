```python
"""Geohash neighbor computation.

Implements geohash encode/decode and 8-connected neighbor lookup using the
standard base32 geohash alphabet, operating directly on the interleaved
latitude/longitude bit grids for exact, floating-point-free results.
"""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_INDEX = {c: i for i, c in enumerate(_BASE32)}


def _decode_bits(gh):
    lat_bits = 0
    lon_bits = 0
    lat_bit_count = 0
    lon_bit_count = 0
    even = True
    for c in gh:
        cd = _BASE32_INDEX[c]
        for mask in (16, 8, 4, 2, 1):
            bit = 1 if cd & mask else 0
            if even:
                lon_bits = (lon_bits << 1) | bit
                lon_bit_count += 1
            else:
                lat_bits = (lat_bits << 1) | bit
                lat_bit_count += 1
            even = not even
    return lat_bits, lon_bits, lat_bit_count, lon_bit_count


def _encode_bits(lat_bits, lon_bits, lat_bit_count, lon_bit_count):
    total_bits = lat_bit_count + lon_bit_count
    out = []
    ch = 0
    nbits = 0
    even = True
    li = lon_bit_count - 1
    la = lat_bit_count - 1
    for _ in range(total_bits):
        if even:
            b = (lon_bits >> li) & 1
            li -= 1
        else:
            b = (lat_bits >> la) & 1
            la -= 1
        ch = (ch << 1) | b
        nbits += 1
        if nbits == 5:
            out.append(_BASE32[ch])
            ch = 0
            nbits = 0
        even = not even
    return "".join(out)


def geohash_neighbors(gh):
    """Return the geohashes (at the same precision) of the up to 8 cells
    surrounding ``gh``. East/west neighbours wrap across the antimeridian;
    neighbours that would fall beyond a pole are omitted."""
    lat_bits, lon_bits, lat_bit_count, lon_bit_count = _decode_bits(gh)
    lat_max = 1 << lat_bit_count
    lon_max = 1 << lon_bit_count

    neighbors = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            new_lat_bits = lat_bits + dlat
            if new_lat_bits < 0 or new_lat_bits >= lat_max:
                continue
            new_lon_bits = (lon_bits + dlon) % lon_max
            neighbors.append(
                _encode_bits(new_lat_bits, new_lon_bits, lat_bit_count, lon_bit_count)
            )
    return neighbors
```