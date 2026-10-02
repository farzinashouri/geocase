# Geohash neighbor calculation module.
# Provides geohash_neighbors(gh) returning the 8 surrounding geohashes at the same precision.
# East/west neighbors wrap across the antimeridian; polar neighbors are omitted.

BASE32_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_DECODE = {ch: i for i, ch in enumerate(BASE32_ALPHABET)}
_BASE32_ENCODE = BASE32_ALPHABET


def _geohash_decode(gh: str):
    """Decode geohash string into integer (lon_index, lat_index) and precision."""
    gh = gh.lower()
    lon = 0
    lat = 0
    is_lon = True  # start with longitude bit
    for ch in gh:
        val = _BASE32_DECODE[ch]
        for shift in (4, 3, 2, 1, 0):  # process 5 bits from most to least significant
            bit = (val >> shift) & 1
            if is_lon:
                lon = (lon << 1) | bit
            else:
                lat = (lat << 1) | bit
            is_lon = not is_lon
    return lon, lat, len(gh)


def _geohash_encode(lon: int, lat: int, precision: int) -> str:
    """Encode integer (lon_index, lat_index) into a geohash string of given precision."""
    lon_bits = (5 * precision + 1) // 2   # ceil(5*precision/2)
    lat_bits = (5 * precision) // 2       # floor(5*precision/2)

    # Extract bits from most significant to least significant
    lon_bit_list = [(lon >> (lon_bits - 1 - i)) & 1 for i in range(lon_bits)]
    lat_bit_list = [(lat >> (lat_bits - 1 - i)) & 1 for i in range(lat_bits)]

    # Interleave bits: even positions (0,2,4,...) are longitude, odd are latitude
    bits = []
    li = la = 0
    for pos in range(5 * precision):
        if pos % 2 == 0:
            bits.append(lon_bit_list[li])
            li += 1
        else:
            bits.append(lat_bit_list[la])
            la += 1

    # Pack bits into base32 characters
    chars = []
    for i in range(0, 5 * precision, 5):
        val = 0
        for b in bits[i:i+5]:
            val = (val << 1) | b
        chars.append(_BASE32_ENCODE[val])
    return ''.join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """
    Return the 8 geohash neighbors of `gh` at the same precision.
    East/west neighbors wrap around the antimeridian.
    Neighbors beyond the poles are omitted.
    """
    if not gh:
        return []

    precision = len(gh)
    lon, lat, _ = _geohash_decode(gh)

    lon_bits = (5 * precision + 1) // 2
    lat_bits = (5 * precision) // 2
    max_lon = 1 << lon_bits
    max_lat = 1 << lat_bits

    neighbors = []
    for d_lon in (-1, 0, 1):
        for d_lat in (-1, 0, 1):
            if d_lon == 0 and d_lat == 0:
                continue
            n_lon = (lon + d_lon) % max_lon          # wrap east/west
            n_lat = lat + d_lat
            if 0 <= n_lat < max_lat:                 # omit polar overflow
                neighbors.append(_geohash_encode(n_lon, n_lat, precision))
    return neighbors