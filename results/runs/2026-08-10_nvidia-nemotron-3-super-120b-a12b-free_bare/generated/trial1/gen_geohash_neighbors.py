"""
geohash_neighbors.py

Provides a single function `geohash_neighbors(gh)` that returns the geohashes
(of the same precision) of the eight cells surrounding the cell identified by
the geohash `gh`. Cells beyond the poles are omitted, and east/west neighbours
wrap across the antimeridian.

The implementation uses only the Python standard library.
"""

# Base32 map used by the geohash algorithm
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_MAP = {ch: i for i, ch in enumerate(_BASE32)}


def _decode_geohash(gh: str):
    """
    Decode a geohash to its latitude, longitude and the cell's bounding box.
    Returns (lat, lon, (lat_min, lat_max, lon_min, lon_max)).
    """
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_even = True  # longitude first

    for ch in gh:
        cd = _BASE32_MAP[ch]
        for i in range(4, -1, -1):  # process bits from most to least significant
            bit = (cd >> i) & 1
            if is_even:  # longitude
                mid = (lon_min + lon_max) / 2.0
                if bit == 0:
                    lon_max = mid
                else:
                    lon_min = mid
            else:  # latitude
                mid = (lat_min + lat_max) / 2.0
                if bit == 0:
                    lat_max = mid
                else:
                    lat_min = mid
            is_even = not is_even

    lat = (lat_min + lat_max) / 2.0
    lon = (lon_min + lon_max) / 2.0
    return lat, lon, (lat_min, lat_max, lon_min, lon_max)


def _encode_geohash(lat: float, lon: float, precision: int) -> str:
    """
    Encode a latitude/longitude pair to a geohash of the given precision.
    """
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_even = True
    bits = []

    while len(bits) < precision * 5:
        if is_even:  # longitude
            mid = (lon_min + lon_max) / 2.0
            if lon >= mid:
                bits.append(1)
                lon_min = mid
            else:
                bits.append(0)
                lon_max = mid
        else:  # latitude
            mid = (lat_min + lat_max) / 2.0
            if lat >= mid:
                bits.append(1)
                lat_min = mid
            else:
                bits.append(0)
                lat_max = mid
        is_even = not is_even

    # Convert bits to base32 characters
    geohash = []
    for i in range(0, len(bits), 5):
        chunk = bits[i:i + 5]
        # Pad with zeros if needed (should not happen because length is multiple of 5)
        while len(chunk) < 5:
            chunk.append(0)
        val = sum(b << (4 - idx) for idx, b in enumerate(chunk))
        geohash.append(_BASE32[val])
    return "".join(geohash)


def _wrap_lon(lon: float) -> float:
    """Wrap longitude to the interval [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def geohash_neighbors(gh: str):
    """
    Return a list of geohash strings (same precision as `gh`) representing the
    eight cells surrounding the cell identified by `gh`. Cells that would fall
    outside the latitude range [-90, 90] are omitted. East/west neighbours wrap
    across the antimeridian.

    Parameters
    ----------
    gh : str
        A valid geohash.

    Returns
    -------
    List[str]
        List of neighbouring geohashes (order not guaranteed).
    """
    if not gh:
        return []

    precision = len(gh)
    lat, lon, (lat_min, lat_max, lon_min, lon_max) = _decode_geohash(gh)

    lat_size = lat_max - lat_min
    lon_size = lon_max - lon_min

    neighbours = []
    dlat_options = (-lat_size, 0.0, lat_size)
    dlon_options = (-lon_size, 0.0, lon_size)

    for dlat in dlat_options:
        for dlon in dlon_options:
            if dlat == 0.0 and dlon == 0.0:
                continue  # skip the cell itself
            nlat = lat + dlat
            nlon = _wrap_lon(lon + dlon)
            if nlat < -90.0 or nlat > 90.0:
                continue  # beyond a pole – omit
            ngeohash = _encode_geohash(nlat, nlon, precision)
            neighbours.append(ngeohash)

    return neighbours