"""
Geohash neighbor calculation module.

Provides a function `geohash_neighbors(gh)` that returns the 8 surrounding
geohashes at the same precision. Longitude wraps across the antimeridian;
neighbors beyond the poles are omitted.
"""

_BASE32_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_DECODE_MAP = {c: i for i, c in enumerate(_BASE32_ALPHABET)}


def _decode_geohash(gh: str):
    """Decode a geohash string into integer grid coordinates (x, y) and bit lengths."""
    n = len(gh) * 5
    hash_int = 0
    for ch in gh:
        hash_int = (hash_int << 5) | _BASE32_DECODE_MAP[ch]

    lon_bits = (n + 1) // 2
    lat_bits = n // 2

    x = 0
    y = 0
    # De-interleave bits from most significant to least significant.
    for i in range(n):
        bit = (hash_int >> (n - 1 - i)) & 1
        if i % 2 == 0:  # even index -> longitude bit
            x = (x << 1) | bit
        else:           # odd index -> latitude bit
            y = (y << 1) | bit
    return x, y, lon_bits, lat_bits


def _encode_geohash(x: int, y: int, lon_bits: int, lat_bits: int, precision: int) -> str:
    """Encode integer grid coordinates back into a geohash string of given precision."""
    n = 5 * precision
    hash_int = 0
    # Interleave bits: start with most significant bit of longitude, then latitude, etc.
    for k in range(lon_bits):
        bit_x = (x >> (lon_bits - 1 - k)) & 1
        hash_int = (hash_int << 1) | bit_x
        if k < lat_bits:
            bit_y = (y >> (lat_bits - 1 - k)) & 1
            hash_int = (hash_int << 1) | bit_y

    # Convert to base32 string of fixed length.
    chars = []
    for i in range(precision):
        shift = n - 5 * (i + 1)
        chunk = (hash_int >> shift) & 0x1F
        chars.append(_BASE32_ALPHABET[chunk])
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """
    Return the geohashes of the 8 cells surrounding `gh` at the same precision.

    Longitude wraps across the antimeridian. Cells beyond the poles (latitude
    > 90° or < -90°) do not exist and are omitted, so a cell touching a pole
    yields fewer than 8 neighbors.

    Parameters
    ----------
    gh: str
        A valid geohash string (lowercase).

    Returns
    -------
    list[str]
        List of neighbor geohash strings (order not guaranteed).
    """
    x, y, lon_bits, lat_bits = _decode_geohash(gh)
    precision = len(gh)
    lon_max = 1 << lon_bits
    lat_max = 1 << lat_bits

    neighbors = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx = (x + dx) % lon_max          # wrap longitude
            ny = y + dy
            if 0 <= ny < lat_max:            # omit polar overflow
                neighbors.append(_encode_geohash(nx, ny, lon_bits, lat_bits, precision))
    return neighbors