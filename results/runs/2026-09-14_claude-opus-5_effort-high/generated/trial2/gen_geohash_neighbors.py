"""Geohash neighbour lookup.

A geohash of precision ``p`` encodes ``5 * p`` bits that alternate between
longitude and latitude, starting with longitude.  The bits therefore describe a
cell in a regular grid with ``2 ** ceil(5p/2)`` columns and ``2 ** floor(5p/2)``
rows, and neighbour lookup is exact integer arithmetic on those indices -- no
floating point decoding is involved.

Columns wrap across the antimeridian; rows do not wrap, so a cell touching a
pole has fewer than eight neighbours.

Importing this module has no side effects.
"""

from typing import List, Tuple

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _to_grid(gh: str) -> Tuple[int, int, int, int]:
    """Return ``(row, col, lat_bits, lon_bits)`` for a geohash string."""
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string, got %r" % type(gh).__name__)
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    row = col = 0
    lat_bits = lon_bits = 0
    for char in gh.lower():
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError("invalid geohash character: %r" % char) from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            # Even-indexed bits (longitude) come first in every character pair.
            if (lon_bits + lat_bits) % 2 == 0:
                col = (col << 1) | bit
                lon_bits += 1
            else:
                row = (row << 1) | bit
                lat_bits += 1
    return row, col, lat_bits, lon_bits


def _to_geohash(row: int, col: int, lat_bits: int, lon_bits: int) -> str:
    """Inverse of :func:`_to_grid`."""
    chars = []
    value = 0
    filled = 0
    total = lat_bits + lon_bits
    for i in range(total):
        if i % 2 == 0:
            bit = (col >> (lon_bits - 1 - i // 2)) & 1
        else:
            bit = (row >> (lat_bits - 1 - i // 2)) & 1
        value = (value << 1) | bit
        filled += 1
        if filled == 5:
            chars.append(_BASE32[value])
            value = 0
            filled = 0
    return "".join(chars)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the cells surrounding ``gh``.

    The result contains the up-to-eight neighbouring cells at the same
    precision as ``gh``, in unspecified order.  East/west neighbours wrap
    across the antimeridian.  Cells beyond the north or south pole do not
    exist and are omitted, so a cell in the top or bottom row of the grid has
    only five neighbours (three for a precision-1 pole cell is impossible --
    the grid always has at least four rows and eight columns).

    Parameters
    ----------
    gh:
        A geohash string.  Case-insensitive; results are lowercase.

    Raises
    ------
    ValueError
        If ``gh`` is empty or contains a character outside the geohash
        base-32 alphabet.
    """
    row, col, lat_bits, lon_bits = _to_grid(gh)
    n_rows = 1 << lat_bits
    n_cols = 1 << lon_bits

    neighbors = []
    for d_row in (1, 0, -1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            r = row + d_row
            if not 0 <= r < n_rows:
                continue  # past a pole: no such cell
            c = (col + d_col) % n_cols  # wraps at the antimeridian
            neighbors.append(_to_geohash(r, c, lat_bits, lon_bits))
    return neighbors