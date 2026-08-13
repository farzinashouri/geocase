```python
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
BASE32_MAP = {c: i for i, c in enumerate(BASE32)}

def geohash_neighbors(gh):
    """Return the 8 neighboring geohashes at the same precision.

    East/west neighbors wrap across the antimeridian.
    Neighbors beyond the poles are omitted.
    """
    gh = gh.lower()
    L = len(gh)
    total_bits = 5 * L
    lon_bits = (total_bits + 1) // 2
    lat_bits = total_bits // 2

    # Decode geohash to integer coordinates (lon_int, lat_int)
    lon_int = 0
    lat_int = 0
    for i, ch in enumerate(gh):
        val = BASE32_MAP[ch]
        for bit_pos in range(4, -1, -1):
            bit = (val >> bit_pos) & 1
            combined_index = i * 5 + (4 - bit_pos)
            if combined_index % 2 == 0:
                lon_int = (lon_int << 1) | bit
            else:
                lat_int = (lat_int << 1) | bit

    max_lon = 1 << lon_bits
    max_lat = 1 << lat_bits
    neighbors = []

    for d_lon in (-1, 0, 1):
        for d_lat in (-1, 0, 1):
            if d_lon == 0 and d_lat == 0:
                continue
            new_lon = (lon_int + d_lon) % max_lon
            new_lat = lat_int + d_lat
            if new_lat < 0 or new_lat >= max_lat:
                continue

            # Encode (new_lon, new_lat) back to geohash of length L
            combined = 0
            for i in range(total_bits):
                combined <<= 1
                if i % 2 == 0:
                    bit_index = lon_bits - 1 - (i // 2)
                    bit = (new_lon >> bit_index) & 1
                else:
                    bit_index = lat_bits - 1 - (i // 2)
                    bit = (new_lat >> bit_index) & 1
                combined |= bit

            chars = []
            for i in range(L):
                shift = total_bits - 5 * (i + 1)
                chunk = (combined >> shift) & 0x1F
                chars.append(BASE32[chunk])
            neighbors.append(''.join(chars))

    return neighbors
```