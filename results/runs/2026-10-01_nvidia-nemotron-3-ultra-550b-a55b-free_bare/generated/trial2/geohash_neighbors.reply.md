```python
"""
Geohash neighbor calculation module.

Provides a function `geohash_neighbors(gh)` that returns the 8 surrounding
geohashes at the same precision. Longitude wraps across the antimeridian;
neighbors beyond the poles are omitted.
"""

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
BASE32_MAP = {c: i for i, c in enumerate(BASE32)}


def _decode_geohash(gh: str):
    """Decode a geohash into its latitude/longitude bounding box.

    Returns:
        (lat_min, lat_max, lon_min, lon_max)
    """
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True  # start with longitude bit
    for ch in gh:
        val = BASE32_MAP[ch]
        for shift in (4, 3, 2, 1, 0):  # 5 bits per character, MSB first
            bit = (val >> shift) & 1
            if is_lon:
                mid = (lon_min + lon_max) / 2.0
                if bit:
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2.0
                if bit:
                    lat_min = mid
                else:
                    lat_max = mid
            is_lon = not is_lon
    return lat_min, lat_max, lon_min, lon_max


def _encode_geohash(lat: float, lon: float, precision: int) -> str:
    """Encode a latitude/longitude into a geohash of given precision."""
    # Normalize longitude to [-180, 180)
    while lon >= 180.0:
        lon -= 360.0
    while lon < -180.0:
        lon += 360.0

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True
    bits = 0
    bit_count = 0
    out = []

    for _ in range(precision * 5):
        if is_lon:
            mid = (lon_min + lon_max) / 2.0
            if lon >= mid:
                bits = (bits << 1) | 1
                lon_min = mid
            else:
                bits = (bits << 1) | 0
                lon_max = mid
        else:
            mid = (lat_min + lat_max) / 2.0
            if lat >= mid:
                bits = (bits << 1) | 1
                lat_min = mid
            else:
                bits = (bits << 1) | 0
                lat_max = mid
        is_lon = not is_lon
        bit_count += 1
        if bit_count == 5:
            out.append(BASE32[bits])
            bits = 0
            bit_count = 0

    return "".join(out)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the 8 neighboring geohashes at the same precision.

    The list order is not guaranteed. Neighbors across the antimeridian are
    included (longitude wraps). Cells beyond the poles (latitude > 90 or < -90)
    are omitted.
    """
    lat_min, lat_max, lon_min, lon_max = _decode_geohash(gh)
    center_lat = (lat_min + lat_max) / 2.0
    center_lon = (lon_min + lon_max) / 2.0
    height = lat_max - lat_min
    width = lon_max - lon_min
    precision = len(gh)

    neighbors = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            n_lon = center_lon + dx * width
            n_lat = center_lat + dy * height

            # Wrap longitude
            while n_lon >= 180.0:
                n_lon -= 360.0
            while n_lon < -180.0:
                n_lon += 360.0

            # Omit neighbors beyond the poles
            if n_lat < -90.0 or n_lat > 90.0:
                continue

            neighbors.append(_encode_geohash(n_lat, n_lon, precision))

    return neighbors
```