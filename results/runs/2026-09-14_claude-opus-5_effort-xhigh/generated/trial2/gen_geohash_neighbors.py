"""Geohash cell adjacency.

Exposes :func:`geohash_neighbors`, which returns the geohashes of the cells
surrounding a given cell at the same precision.

A geohash is a bit-interleaved pair of indices: the bit stream alternates
longitude, latitude, ... starting with longitude, most significant bit first.
Peeling that stream apart yields the cell's integer column (longitude) and row
(latitude) on a 2**lon_bits by 2**lat_bits grid. Adjacency is then plain
integer arithmetic on those indices, which is exact at every precision --- no
floating-point centres or epsilons that can drift across a cell boundary.

Columns are cyclic, so east/west steps wrap across the antimeridian. Rows are
not: a step off the top or bottom row names no cell, so those neighbours are
omitted and a cell touching a pole has five neighbours (three at a corner of
the grid is impossible, since the column axis always wraps).
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _to_indices(gh):
    """Split a geohash into ``(row, col, lat_bits, lon_bits)``."""
    row = col = 0
    lat_bits = lon_bits = 0
    i = 0
    for ch in gh:
        try:
            val = _DECODE[ch]
        except KeyError:
            raise ValueError(f"not a valid geohash character: {ch!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (val >> shift) & 1
            if i % 2 == 0:
                col = (col << 1) | bit
                lon_bits += 1
            else:
                row = (row << 1) | bit
                lat_bits += 1
            i += 1
    return row, col, lat_bits, lon_bits


def _from_indices(row, col, lat_bits, lon_bits):
    """Re-interleave row/column indices back into a geohash string."""
    out = []
    acc = nbits = 0
    lat_pos = lat_bits - 1
    lon_pos = lon_bits - 1
    for i in range(lat_bits + lon_bits):
        if i % 2 == 0:
            bit = (col >> lon_pos) & 1
            lon_pos -= 1
        else:
            bit = (row >> lat_pos) & 1
            lat_pos -= 1
        acc = (acc << 1) | bit
        nbits += 1
        if nbits == 5:
            out.append(_BASE32[acc])
            acc = nbits = 0
    return "".join(out)


def geohash_neighbors(gh):
    """Return the geohashes of the cells surrounding ``gh``.

    Parameters
    ----------
    gh:
        A geohash string of any precision. Case-insensitive; the standard
        geohash alphabet excludes ``a``, ``i``, ``l`` and ``o``.

    Returns
    -------
    list of str
        The surrounding cells at the same precision as ``gh``, lowercase, in
        unspecified order. Normally eight entries; five when ``gh`` lies in the
        top or bottom row of the grid, since the cells beyond a pole do not
        exist. East and west neighbours wrap across the antimeridian.

    Raises
    ------
    TypeError
        If ``gh`` is not a string.
    ValueError
        If ``gh`` is empty or contains a character outside the geohash
        alphabet.

    Examples
    --------
    >>> sorted(geohash_neighbors("u"))
    ['e', 'g', 's', 't', 'v']
    >>> "b" in geohash_neighbors("z")  # wraps the antimeridian
    True
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a string, got {type(gh).__name__}")
    key = gh.lower()
    if not key:
        raise ValueError("geohash must be a non-empty string")

    row, col, lat_bits, lon_bits = _to_indices(key)
    n_rows = 1 << lat_bits
    n_cols = 1 << lon_bits

    neighbors = []
    for drow in (1, 0, -1):
        r = row + drow
        if not 0 <= r < n_rows:
            continue  # past a pole: no cell there
        for dcol in (-1, 0, 1):
            if drow == 0 and dcol == 0:
                continue
            c = (col + dcol) % n_cols
            neighbors.append(_from_indices(r, c, lat_bits, lon_bits))
    return neighbors