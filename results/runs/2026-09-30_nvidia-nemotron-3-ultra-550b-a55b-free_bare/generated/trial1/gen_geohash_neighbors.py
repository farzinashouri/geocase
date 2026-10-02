BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
DECODE_MAP = {c: i for i, c in enumerate(BASE32)}

def _decode_indices(geohash):
    """Decode a geohash into its integer grid indices and bit counts."""
    lon_index = 0
    lat_index = 0
    lon_bits = 0
    lat_bits = 0
    bit = 0
    for c in geohash:
        cd = DECODE_MAP[c]
        for mask in (16, 8, 4, 2, 1):  # 5 bits from MSB to LSB
            if bit % 2 == 0:  # longitude bit
                lon_index = (lon_index << 1) | (1 if (cd & mask) else 0)
                lon_bits += 1
            else:  # latitude bit
                lat_index = (lat_index << 1) | (1 if (cd & mask) else 0)
                lat_bits += 1
            bit += 1
    return lon_index, lat_index, lon_bits, lat_bits

def _encode_indices(lon_index, lat_index, lon_bits, lat_bits):
    """Encode integer grid indices back into a geohash string."""
    total_bits = lon_bits + lat_bits
    precision = total_bits // 5
    bits = 0
    # Interleave bits: most significant bits first, alternating lon/lat.
    for k in range(lon_bits):
        bits = (bits << 1) | ((lon_index >> (lon_bits - 1 - k)) & 1)
        if k < lat_bits:
            bits = (bits << 1) | ((lat_index >> (lat_bits - 1 - k)) & 1)
    # Convert the combined bit string to base32.
    geohash = []
    for i in range(precision):
        shift = total_bits - 5 * (i + 1)
        val = (bits >> shift) & 31
        geohash.append(BASE32[val])
    return ''.join(geohash)

def geohash_neighbors(gh):
    """
    Return the 8 neighboring geohashes at the same precision.
    East/west neighbors wrap across the antimeridian; neighbors beyond the poles are omitted.
    """
    if not gh:
        return []
    gh = gh.strip().lower()
    lon_index, lat_index, lon_bits, lat_bits = _decode_indices(gh)
    max_lon = (1 << lon_bits) - 1
    max_lat = (1 << lat_bits) - 1

    # (d_lon, d_lat) for N, NE, E, SE, S, SW, W, NW
    directions = [
        (0, 1),   # N
        (1, 1),   # NE
        (1, 0),   # E
        (1, -1),  # SE
        (0, -1),  # S
        (-1, -1), # SW
        (-1, 0),  # W
        (-1, 1),  # NW
    ]

    neighbors = []
    for d_lon, d_lat in directions:
        new_lon = lon_index + d_lon
        new_lat = lat_index + d_lat

        # Longitude wraps around the antimeridian.
        if new_lon < 0:
            new_lon = max_lon
        elif new_lon > max_lon:
            new_lon = 0

        # Latitude has hard limits at the poles.
        if new_lat < 0 or new_lat > max_lat:
            continue

        neighbors.append(_encode_indices(new_lon, new_lat, lon_bits, lat_bits))

    return neighbors