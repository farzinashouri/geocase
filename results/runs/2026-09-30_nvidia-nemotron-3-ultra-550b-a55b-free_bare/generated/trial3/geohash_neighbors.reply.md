```python
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(BASE32)}


def _decode_geohash(gh: str):
    """Decode a geohash into integer grid indices and bit lengths."""
    lon_index = 0
    lat_index = 0
    is_lon = True
    for ch in gh:
        val = _DECODE_MAP[ch]
        for i in range(4, -1, -1):
            bit = (val >> i) & 1
            if is_lon:
                lon_index = (lon_index << 1) | bit
            else:
                lat_index = (lat_index << 1) | bit
            is_lon = not is_lon
    total_bits = 5 * len(gh)
    lon_bits = (total_bits + 1) // 2
    lat_bits = total_bits // 2
    return lon_index, lat_index, lon_bits, lat_bits


def _encode_geohash(lon_index: int, lat_index: int, lon_bits: int, lat_bits: int) -> str:
    """Encode integer grid indices back to a geohash string."""
    bits = []
    total_bits = lon_bits + lat_bits
    for i in range(total_bits):
        if i % 2 == 0:
            bit_index = lon_bits - 1 - (i // 2)
            bits.append((lon_index >> bit_index) & 1)
        else:
            bit_index = lat_bits - 1 - (i // 2)
            bits.append((lat_index >> bit_index) & 1)
    chars = []
    for i in range(0, total_bits, 5):
        val = 0
        for b in bits[i:i+5]:
            val = (val << 1) | b
        chars.append(BASE32[val])
    return ''.join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """
    Return the 8 neighboring geohashes at the same precision.
    East/west neighbors wrap across the antimeridian; neighbors beyond the poles are omitted.
    """
    lon_index, lat_index, lon_bits, lat_bits = _decode_geohash(gh)
    lon_size = 1 << lon_bits
    lat_size = 1 << lat_bits

    neighbors = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            new_lon = (lon_index + dx) % lon_size
            new_lat = lat_index + dy
            if 0 <= new_lat < lat_size:
                neighbors.append(_encode_geohash(new_lon, new_lat, lon_bits, lat_bits))
    return neighbors
```