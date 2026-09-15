"""Geohash neighbour computation.

Provides :func:`geohash_neighbors`, which returns the geohashes of the (up to
eight) cells surrounding a given geohash cell, at the same precision.

The implementation works purely in the integer index space of the geohash
grid, so it is exact: no floating-point latitude/longitude round-tripping is
involved.  A geohash of length ``p`` encodes ``n = 5 * p`` bits, which are
interleaved starting with longitude, giving ``ceil(n / 2)`` longitude bits and
``floor(n / 2)`` latitude bits.  Those bit strings are the column and row
indices of the cell in a regular grid covering ``[-180, 180) x [-90, 90]``.

Neighbour rules follow directly from that grid:

* East/west neighbours wrap around the antimeridian (modulo the column count).
* North/south neighbours beyond a pole simply do not exist and are omitted, so
  a cell touching a pole has fewer than eight neighbours.

Importing this module has no side effects.
"""

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}


def _decode_indices(gh):
    """Return ``(lat_index, lon_index, lat_bits, lon_bits)`` for a geohash."""
    n = 5 * len(gh)
    lon_bits = (n + 1) // 2
    lat_bits = n // 2

    lat_index = 0
    lon_index = 0
    position = 0
    for char in gh:
        try:
            value = _DECODE_MAP[char]
        except KeyError:
            raise ValueError("invalid geohash character: %r" % (char,)) from None
        for shift in range(4, -1, -1):
            bit = (value >> shift) & 1
            if position % 2 == 0:
                lon_index = (lon_index << 1) | bit
            else:
                lat_index = (lat_index << 1) | bit
            position += 1

    return lat_index, lon_index, lat_bits, lon_bits


def _encode_indices(lat_index, lon_index, lat_bits, lon_bits):
    """Inverse of :func:`_decode_indices`."""
    n = lat_bits + lon_bits
    chars = []
    value = 0
    for position in range(n):
        if position % 2 == 0:
            shift = lon_bits - 1 - position // 2
            bit = (lon_index >> shift) & 1
        else:
            shift = lat_bits - 1 - position // 2
            bit = (lat_index >> shift) & 1
        value = (value << 1) | bit
        if position % 5 == 4:
            chars.append(_BASE32[value])
            value = 0
    return "".join(chars)


def geohash_neighbors(gh):
    """Return the geohashes of the cells surrounding ``gh``.

    Parameters
    ----------
    gh : str
        A non-empty geohash string (base-32, case-insensitive).

    Returns
    -------
    list of str
        The neighbouring geohashes at the same precision as ``gh``, in
        unspecified order.  Normally eight entries; fewer for cells that touch
        the north or south pole, since cells beyond a pole do not exist.
        Lowercase, regardless of the case of the input.

    Raises
    ------
    TypeError
        If ``gh`` is not a string.
    ValueError
        If ``gh`` is empty or contains a character that is not part of the
        geohash base-32 alphabet.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string, got %s" % type(gh).__name__)
    gh = gh.lower()
    if not gh:
        raise ValueError("geohash must be non-empty")

    lat_index, lon_index, lat_bits, lon_bits = _decode_indices(gh)
    n_rows = 1 << lat_bits
    n_cols = 1 << lon_bits

    neighbors = []
    for d_lat in (1, 0, -1):
        row = lat_index + d_lat
        if row < 0 or row >= n_rows:
            # Beyond a pole: no such cell.
            continue
        for d_lon in (-1, 0, 1):
            if d_lat == 0 and d_lon == 0:
                continue
            # Wrap across the antimeridian.
            col = (lon_index + d_lon) % n_cols
            neighbors.append(_encode_indices(row, col, lat_bits, lon_bits))

    return neighbors