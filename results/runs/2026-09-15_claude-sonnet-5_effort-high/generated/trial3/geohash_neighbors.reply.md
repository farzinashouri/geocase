```python
"""Compute geohash neighbor cells, handling antimeridian wrap and pole edges."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_CHAR_TO_BITS = {c: i for i, c in enumerate(_BASE32)}


def _decode_bits(gh):
    bits = []
    for c in gh:
        v = _CHAR_TO_BITS[c]
        for i in range(4, -1, -1):
            bits.append((v >> i) & 1)
    return bits


def _encode_bits(bits):
    chars = []
    for i in range(0, len(bits), 5):
        v = 0
        for b in bits[i:i + 5]:
            v = (v << 1) | b
        chars.append(_BASE32[v])
    return "".join(chars)


def geohash_neighbors(gh):
    """Return the geohashes (same precision) of up to 8 cells surrounding `gh`.

    East/west neighbors wrap across the antimeridian. Neighbors that would
    fall beyond the poles do not exist and are omitted from the result.
    """
    gh = gh.lower()
    bits = _decode_bits(gh)
    n = len(bits)

    lon_bits = bits[0::2]
    lat_bits = bits[1::2]
    lon_len = len(lon_bits)
    lat_len = len(lat_bits)

    lon_idx = int("".join(map(str, lon_bits)), 2) if lon_len else 0
    lat_idx = int("".join(map(str, lat_bits)), 2) if lat_len else 0
    lon_range = 1 << lon_len
    lat_range = 1 << lat_len

    neighbors = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue

            new_lat = lat_idx + dlat
            if new_lat < 0 or new_lat >= lat_range:
                # Neighbor would lie beyond a pole; it does not exist.
                continue

            new_lon = (lon_idx + dlon) % lon_range

            new_lon_bits = [(new_lon >> i) & 1 for i in range(lon_len - 1, -1, -1)]
            new_lat_bits = [(new_lat >> i) & 1 for i in range(lat_len - 1, -1, -1)]

            merged = [0] * n
            merged[0::2] = new_lon_bits
            merged[1::2] = new_lat_bits

            neighbors.append(_encode_bits(merged))

    return neighbors
```