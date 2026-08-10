#!/usr/bin/env python3
"""
A minimal self‑contained module to compute the eight neighboring geohashes
of a given geohash string.  The implementation follows the standard
base‑32 geohash algorithm and does not rely on external libraries.
"""

# Base‑32 map used by the geohash algorithm
_BASE32_MAP = "0123456789bcdefghjkmnpqrstuvwxyz"
_CHAR_TO_VALUE = {c: i for i, c in enumerate(_BASE32_MAP)}


def _decode_geohash(gh: str):
    """
    Decode a geohash string into its latitude and longitude bounds.

    Returns:
        (lat_min, lat_max, lon_min, lon_max)
    """
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    is_lon = True  # start with longitude

    for char in gh:
        val = _CHAR_TO_VALUE[char]
        for i in range(5)[::-1]:  # 5 bits per character, from MSB to LSB
            bit = (val >> i) & 1
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bit:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bit:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_lon = not is_lon

    return lat_range[0], lat_range[1], lon_range[0], lon_range[1]


def _encode_geohash(lat: float, lon: float, precision: int) -> str:
    """
    Encode a latitude/longitude pair into a geohash string of the given precision.
    """
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    bits = []
    is_lon = True

    while len(bits) < precision * 5:
        if is_lon:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                bits.append(1)
                lon_range[0] = mid
            else:
                bits.append(0)
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                bits.append(1)
                lat_range[0] = mid
            else:
                bits.append(0)
                lat_range[1] = mid
        is_lon = not is_lon

    # Convert bits to base32 characters
    geohash = []
    for i in range(0, len(bits), 5):
        chunk = bits[i:i + 5]
        val = 0
        for b in chunk:
            val = (val << 1) | b
        geohash.append(_BASE32_MAP[val])

    return "".join(geohash)


def geohash_neighbors(gh: str):
    """
    Return a list of the eight neighboring geohashes (at the same precision)
    surrounding the cell identified by the input geohash `gh`.

    East and west neighbours wrap across the antimeridian.  Cells beyond the
    poles are omitted, so a cell touching a pole may have fewer than eight
    neighbours.

    Parameters
    ----------
    gh : str
        The geohash string of the target cell.

    Returns
    -------
    List[str]
        A list of neighboring geohash strings.  The order is not significant.
    """
    if not gh:
        raise ValueError("Geohash string must not be empty")

    precision = len(gh)
    lat_min, lat_max, lon_min, lon_max = _decode_geohash(gh)
    lat_center = (lat_min + lat_max) / 2
    lon_center = (lon_min + lon_max) / 2
    lat_size = lat_max - lat_min
    lon_size = lon_max - lon_min

    neighbors = []

    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue

            new_lat = lat_center + dlat * lat_size
            new_lon = lon_center + dlon * lon_size

            # Wrap longitude across the antimeridian
            if new_lon < -180.0:
                new_lon += 360.0
            elif new_lon > 180.0:
                new_lon -= 360.0

            # Skip cells beyond the poles
            if new_lat < -90.0 or new_lat > 90.0:
                continue

            neighbors.append(_encode_geohash(new_lat, new_lon, precision))

    return neighbors