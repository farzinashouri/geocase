```python
"""
Geohash neighbor computation module.

Provides a function `geohash_neighbors(gh)` that returns the 8 surrounding
geohashes at the same precision. Longitude wraps across the antimeridian;
latitude does not wrap (neighbors beyond the poles are omitted).
"""

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_MAP = {c: i for i, c in enumerate(BASE32)}


def _decode_geohash_to_indices(gh: str):
    """Decode a geohash string into integer grid indices (i, j) and bit lengths."""
    gh = gh.lower()
    bits = []
    for ch in gh:
        val = _BASE32_MAP[ch]
        # Extract 5 bits, most significant first
        for shift in range(4, -1, -1):
            bits.append((val >> shift) & 1)

    # Bits are interleaved: even positions -> longitude, odd -> latitude
    lon_bits = bits[0::2]
    lat_bits = bits[1::2]

    # Convert bit lists to integers (most significant bit first)
    i = 0
    for b in lon_bits:
        i = (i << 1) | b
    j = 0
    for b in lat_bits:
        j = (j << 1) | b

    return i, j, len(lon_bits), len(lat_bits)


def _encode_indices_to_geohash(i: int, j: int, lon_bits: int, lat_bits: int) -> str:
    """Encode integer grid indices back to a geohash string of given precision."""
    # Build bit lists (MSB first) of the required lengths
    lon_bit_list = [(i >> (lon_bits - 1 - k)) & 1 for k in range(lon_bits)]
    lat_bit_list = [(j >> (lat_bits - 1 - k)) & 1 for k in range(lat_bits)]

    # Interleave: lon, lat, lon, lat, ...
    bits = []
    for k in range(max(lon_bits, lat_bits)):
        if k < lon_bits:
            bits.append(lon_bit_list[k])
        if k < lat_bits:
            bits.append(lat_bit_list[k])

    # Group into 5-bit chunks and map to base32
    chars = []
    for idx in range(0, len(bits), 5):
        chunk = bits[idx:idx + 5]
        val = 0
        for b in chunk:
            val = (val << 1) | b
        chars.append(BASE32[val])
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """
    Return the geohashes of the 8 neighboring cells at the same precision.

    The order of the returned list is not specified. East/west neighbors wrap
    across the antimeridian; neighbors beyond the poles (latitude > 90 or < -90)
    are omitted.
    """
    i, j, lon_bits, lat_bits = _decode_geohash_to_indices(gh)
    lon_divisions = 1 << lon_bits
    lat_divisions = 1 << lat_bits

    neighbors = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            ni = (i + di) % lon_divisions  # longitude wraps
            nj = j + dj                    # latitude does not wrap
            if 0 <= nj < lat_divisions:
                neighbors.append(_encode_indices_to_geohash(ni, nj, lon_bits, lat_bits))
    return neighbors
```