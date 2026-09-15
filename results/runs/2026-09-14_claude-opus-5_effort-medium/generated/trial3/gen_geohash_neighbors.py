"""Geohash neighbour computation.

Provides :func:`geohash_neighbors`, which returns the geohashes of the (up to
eight) cells surrounding a given geohash cell, at the same precision.

The work is done on the integer row/column indices that a geohash encodes,
rather than on floating point coordinates, so the result is exact at every
precision.  A geohash of length ``n`` carries ``5 * n`` bits, interleaved
longitude-first: bits at even positions refine the longitude, bits at odd
positions refine the latitude.  That gives ``ceil(5n/2)`` longitude bits
(columns) and ``floor(5n/2)`` latitude bits (rows).

East/west neighbours wrap around the antimeridian (columns are cyclic).
North/south neighbours past a pole do not exist and are omitted, so a cell
touching a pole has fewer than eight neighbours.
"""

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}


def _split(gh):
    """Return ``(lon_index, lat_index, lon_bits, lat_bits)`` for a geohash."""
    lon = 0
    lat = 0
    lon_bits = 0
    lat_bits = 0
    position = 0
    for char in gh:
        try:
            value = _DECODE_MAP[char]
        except KeyError:
            raise ValueError(
                "invalid geohash character {0!r} in {1!r}".format(char, gh)
            ) from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if position % 2 == 0:
                lon = (lon << 1) | bit
                lon_bits += 1
            else:
                lat = (lat << 1) | bit
                lat_bits += 1
            position += 1
    return lon, lat, lon_bits, lat_bits


def _join(lon, lat, lon_bits, lat_bits):
    """Interleave longitude/latitude indices back into a geohash string."""
    total = lon_bits + lat_bits
    lon_left = lon_bits
    lat_left = lat_bits
    chars = []
    value = 0
    filled = 0
    for position in range(total):
        if position % 2 == 0:
            lon_left -= 1
            bit = (lon >> lon_left) & 1
        else:
            lat_left -= 1
            bit = (lat >> lat_left) & 1
        value = (value << 1) | bit
        filled += 1
        if filled == 5:
            chars.append(_BASE32[value])
            value = 0
            filled = 0
    return "".join(chars)


def geohash_neighbors(gh):
    """Return the geohashes of the cells surrounding ``gh``.

    Parameters
    ----------
    gh : str
        A geohash string (case insensitive).

    Returns
    -------
    list of str
        The surrounding cells at the same precision as ``gh``, lowercase, in
        no particular order.  Normally eight entries; cells adjacent to a pole
        have fewer, because the rows beyond the pole do not exist.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string, got {0!r}".format(type(gh).__name__))
    gh = gh.strip().lower()
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    lon, lat, lon_bits, lat_bits = _split(gh)
    columns = 1 << lon_bits
    rows = 1 << lat_bits

    neighbors = []
    seen = set()
    for d_lat in (1, 0, -1):
        for d_lon in (-1, 0, 1):
            if d_lat == 0 and d_lon == 0:
                continue
            new_lat = lat + d_lat
            if not 0 <= new_lat < rows:
                # Beyond the north or south pole: no such cell.
                continue
            new_lon = (lon + d_lon) % columns  # wrap across the antimeridian
            neighbor = _join(new_lon, new_lat, lon_bits, lat_bits)
            if neighbor not in seen:
                seen.add(neighbor)
                neighbors.append(neighbor)
    return neighbors