```python
"""Neighbour lookup for geohash cells.

A geohash string encodes an interleaved pair of integer grid indices: bit 0 of
the bit stream is the most significant longitude bit, bit 1 the most
significant latitude bit, and so on.  Working directly on those two integers
makes neighbour lookup exact -- no floating point, so cells adjacent to a grid
boundary cannot be mis-assigned by rounding.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {char: value for value, char in enumerate(_BASE32)}


def _split(gh):
    """Return ``(lon, lon_bits, lat, lat_bits)`` for a geohash string."""
    lon = lat = 0
    lon_bits = lat_bits = 0
    even = True  # even bit positions carry longitude
    for char in gh:
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError("invalid geohash character: {!r}".format(char)) from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if even:
                lon = (lon << 1) | bit
                lon_bits += 1
            else:
                lat = (lat << 1) | bit
                lat_bits += 1
            even = not even
    return lon, lon_bits, lat, lat_bits


def _merge(lon, lon_bits, lat, lat_bits):
    """Inverse of :func:`_split`."""
    out = []
    acc = 0
    filled = 0
    for position in range(lon_bits + lat_bits):
        index = position // 2
        if position % 2 == 0:
            bit = (lon >> (lon_bits - 1 - index)) & 1
        else:
            bit = (lat >> (lat_bits - 1 - index)) & 1
        acc = (acc << 1) | bit
        filled += 1
        if filled == 5:
            out.append(_BASE32[acc])
            acc = 0
            filled = 0
    return "".join(out)


def geohash_neighbors(gh):
    """Return the geohashes of the cells surrounding ``gh``.

    The result holds up to eight geohashes of the same precision as ``gh``, in
    unspecified order.  Longitude wraps across the antimeridian; latitude does
    not, so a cell touching a pole has no neighbours on that side and fewer
    than eight are returned.

    Input is case-insensitive.  Raises :class:`ValueError` for an empty string
    or one containing a character outside the geohash base-32 alphabet, and
    :class:`TypeError` if ``gh`` is not a string.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string, got {}".format(type(gh).__name__))
    gh = gh.strip().lower()
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    lon, lon_bits, lat, lat_bits = _split(gh)
    lon_cells = 1 << lon_bits
    lat_cells = 1 << lat_bits

    neighbors = []
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            next_lat = lat + dlat
            if not 0 <= next_lat < lat_cells:
                continue  # beyond a pole: no such cell
            next_lon = (lon + dlon) % lon_cells
            neighbors.append(_merge(next_lon, lon_bits, next_lat, lat_bits))
    return neighbors
```