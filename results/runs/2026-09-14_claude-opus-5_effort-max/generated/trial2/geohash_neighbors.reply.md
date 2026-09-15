Shell and file-write permissions weren't granted, so I verified the bit math by hand instead of running it: `ezs42` splits into row 3017 / column 3968 (lat 42.583–42.627, lon −5.625–−5.581 ✓), its north neighbour re-encodes to `ezs48` ✓, and at precision 1 the encoder reproduces the canonical level-1 grid bottom row `0 1 4 5 h j n p` ✓ (so `0`'s west neighbour wraps to `p`, and its three southern neighbours are dropped at the pole).

```python
"""Neighbour lookup for geohash cells.

A geohash of length ``n`` carries ``5 * n`` bits that alternate between
longitude (even bit positions, longitude first) and latitude (odd positions).
Pulled apart, those two bit strings are the column and row index of the cell in
a regular ``2 ** lat_bits`` by ``2 ** lon_bits`` grid covering the whole world,
so neighbour lookup is exact integer arithmetic: step the row/column index,
wrap the column across the antimeridian, and drop rows that fall off a pole.
"""

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {char: value for value, char in enumerate(_BASE32)}

# The eight surrounding cells as (row step, column step); rows grow northwards,
# columns grow eastwards.
_DIRECTIONS = (
    (1, -1), (1, 0), (1, 1),
    (0, -1), (0, 1),
    (-1, -1), (-1, 0), (-1, 1),
)


def _split(gh):
    """Return ``(row, column, lat_bits, lon_bits)`` for a geohash string."""
    row = column = 0
    lat_bits = lon_bits = 0
    for index, char in enumerate(gh):
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError(
                f"{char!r} at position {index} is not a base32 geohash character"
            ) from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            # lat_bits + lon_bits is the number of bits read so far, i.e. the
            # position of this bit in the interleaved stream.
            if (lat_bits + lon_bits) % 2 == 0:
                column = (column << 1) | bit
                lon_bits += 1
            else:
                row = (row << 1) | bit
                lat_bits += 1
    return row, column, lat_bits, lon_bits


def _join(row, column, lat_bits, lon_bits):
    """Interleave a row/column index back into a geohash string."""
    lat_seq = [(row >> shift) & 1 for shift in range(lat_bits - 1, -1, -1)]
    lon_seq = [(column >> shift) & 1 for shift in range(lon_bits - 1, -1, -1)]

    chars = []
    value = 0
    filled = 0
    for position in range(lat_bits + lon_bits):
        if position % 2 == 0:
            bit = lon_seq[position // 2]
        else:
            bit = lat_seq[position // 2]
        value = (value << 1) | bit
        filled += 1
        if filled == 5:
            chars.append(_BASE32[value])
            value = 0
            filled = 0
    return "".join(chars)


def geohash_neighbors(gh):
    """Return the geohashes of the eight cells surrounding ``gh``.

    The neighbours share the precision of ``gh`` and come back in no particular
    order.  East and west neighbours wrap across the antimeridian; cells beyond
    a pole do not exist and are omitted, so a geohash touching a pole has five
    neighbours rather than eight.

    ``gh`` is case-insensitive; the returned geohashes are lowercase.
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a string, got {type(gh).__name__}")
    gh = gh.strip().lower()
    if not gh:
        raise ValueError("geohash must not be empty")

    row, column, lat_bits, lon_bits = _split(gh)
    rows = 1 << lat_bits
    columns = 1 << lon_bits

    neighbors = []
    for row_step, column_step in _DIRECTIONS:
        neighbor_row = row + row_step
        if not 0 <= neighbor_row < rows:
            continue  # past the north or south pole
        neighbor_column = (column + column_step) % columns
        neighbors.append(_join(neighbor_row, neighbor_column, lat_bits, lon_bits))
    return neighbors
```