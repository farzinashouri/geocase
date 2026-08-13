```python
# geohash_neighbors.py
"""
A small self‑contained module to compute the 8 neighboring geohashes
of a given geohash string at the same precision.

The implementation follows the standard geohash algorithm
without external dependencies.
"""

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
BASE32_MAP = {c: i for i, c in enumerate(BASE32)}


def _encode_geohash(lat: float, lon: float, precision: int) -> str:
    """Encode latitude/longitude to a geohash string of given precision."""
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    bits = []
    bit = 0
    even = True
    while len(bits) < precision * 5:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon > mid:
                bits.append(1)
                lon_interval[0] = mid
            else:
                bits.append(0)
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat > mid:
                bits.append(1)
                lat_interval[0] = mid
            else:
                bits.append(0)
                lat_interval[1] = mid
        even = not even
    # Convert bits to base32 string
    geohash = []
    for i in range(0, len(bits), 5):
        chunk = bits[i:i + 5]
        value = 0
        for b in chunk:
            value = (value << 1) | b
        geohash.append(BASE32[value])
    return "".join(geohash)


def _decode_geohash(gh: str):
    """Decode a geohash string to its latitude and longitude bounds."""
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    even = True
    for c in gh:
        if c not in BASE32_MAP:
            raise ValueError(f"Invalid geohash character: {c}")
        bits = BASE32_MAP[c]
        for i in range(4, -1, -1):
            bit = (bits >> i) & 1
            if even:
                mid = (lon_interval[0] + lon_interval[1]) / 2
                if bit:
                    lon_interval[0] = mid
                else:
                    lon_interval[1] = mid
            else:
                mid = (lat_interval[0] + lat_interval[1]) / 2
                if bit:
                    lat_interval[0] = mid
                else:
                    lat_interval[1] = mid
            even = not even
    return lat_interval, lon_interval


def geohash_neighbors(gh: str):
    """
    Return the geohashes of the 8 neighboring cells of the given geohash.
    East and west neighbors wrap across the antimeridian.
    Cells beyond the poles are omitted.
    """
    if not gh:
        raise ValueError("Geohash string must not be empty")

    precision = len(gh)
    lat_interval, lon_interval = _decode_geohash(gh)
    lat_min, lat_max = lat_interval
    lon_min, lon_max = lon_interval
    cell_height = lat_max - lat_min
    cell_width = lon_max - lon_min

    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    # Directions: (dx, dy) where dx is lon shift, dy is lat shift
    directions = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1)
    ]

    neighbors = []
    for dx, dy in directions:
        new_lat = center_lat + dy * cell_height
        new_lon = center_lon + dx * cell_width

        # Wrap longitude across antimeridian
        new_lon = ((new_lon + 180) % 360) - 180

        # Check latitude bounds
        if new_lat - cell_height / 2 < -90 or new_lat + cell_height / 2 > 90:
            continue

        neighbor = _encode_geohash(new_lat, new_lon, precision)
        neighbors.append(neighbor)

    return neighbors
```