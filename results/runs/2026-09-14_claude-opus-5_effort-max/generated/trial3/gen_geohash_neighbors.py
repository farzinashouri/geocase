"""Adjacency between geohash cells.

:func:`geohash_neighbors` returns the geohashes of the cells surrounding a
given cell, at the same precision.  The work is done on the integer row and
column indices that the geohash bits already encode, so the result is exact:
no floating point coordinate is ever formed, and cells near the poles or the
antimeridian need no special tolerance.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {char: value for value, char in enumerate(_BASE32)}


def _to_indices(gh: str) -> tuple[int, int, int, int]:
    """Split a geohash into ``(lat_idx, lon_idx, lat_bits, lon_bits)``.

    Geohash bits alternate between longitude and latitude, most significant
    first, starting with longitude.  Deinterleaving them yields the cell's
    column and row in a ``2 ** lon_bits`` by ``2 ** lat_bits`` grid.
    """
    lat_idx = lon_idx = 0
    lat_bits = lon_bits = 0
    is_lon = True
    for char in gh:
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError(f"{char!r} is not a geohash character") from None
        for shift in range(4, -1, -1):
            bit = (value >> shift) & 1
            if is_lon:
                lon_idx = (lon_idx << 1) | bit
                lon_bits += 1
            else:
                lat_idx = (lat_idx << 1) | bit
                lat_bits += 1
            is_lon = not is_lon
    return lat_idx, lon_idx, lat_bits, lon_bits


def _to_geohash(lat_idx: int, lon_idx: int, lat_bits: int, lon_bits: int) -> str:
    """Re-interleave row and column indices back into a geohash string."""
    chars = []
    value = 0
    filled = 0
    lat_left, lon_left = lat_bits, lon_bits
    for position in range(lat_bits + lon_bits):
        if position % 2 == 0:
            lon_left -= 1
            bit = (lon_idx >> lon_left) & 1
        else:
            lat_left -= 1
            bit = (lat_idx >> lat_left) & 1
        value = (value << 1) | bit
        filled += 1
        if filled == 5:
            chars.append(_BASE32[value])
            value = 0
            filled = 0
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells touching ``gh``, at its precision.

    The surrounding cells are returned in an unspecified order.  East and west
    neighbours wrap across the antimeridian, so every cell has both.  A cell
    against a pole has no row beyond it, so those neighbours are omitted and it
    gets five rather than eight.

    Args:
        gh: A geohash string, upper or lower case.

    Returns:
        A list of geohashes, each the same length as ``gh``.

    Raises:
        TypeError: If ``gh`` is not a string.
        ValueError: If ``gh`` is empty or holds a non-geohash character.
    """
    if not isinstance(gh, str):
        raise TypeError(f"gh must be a str, not {type(gh).__name__}")
    if not gh:
        raise ValueError("gh must be a non-empty geohash string")

    lat_idx, lon_idx, lat_bits, lon_bits = _to_indices(gh.lower())
    lat_count = 1 << lat_bits
    lon_count = 1 << lon_bits

    neighbors = []
    for d_lat in (1, 0, -1):
        for d_lon in (-1, 0, 1):
            if d_lat == 0 and d_lon == 0:
                continue
            lat = lat_idx + d_lat
            if not 0 <= lat < lat_count:
                continue  # Beyond a pole; no such cell exists.
            lon = (lon_idx + d_lon) % lon_count  # Wraps the antimeridian.
            neighbors.append(_to_geohash(lat, lon, lat_bits, lon_bits))
    return neighbors