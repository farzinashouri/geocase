"""Neighbour lookup for geohash cells.

A geohash of length *n* encodes 5*n* interleaved bits: even-indexed bits refine
longitude, odd-indexed bits refine latitude. Splitting those bits back apart
gives an exact integer (row, column) address of the cell in the
2**lat_bits x 2**lon_bits grid at that precision, so neighbours can be found by
integer arithmetic instead of by nudging floating-point coordinates:

* columns (longitude) wrap modulo the grid width, which is exactly the wrap
  across the antimeridian;
* rows (latitude) do not wrap -- a row index outside the grid would lie beyond
  a pole, where no cell exists, so it is omitted. Cells in the top or bottom
  row therefore have 5 neighbours instead of 8.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Tuple

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {char: value for value, char in enumerate(_BASE32)}


def _split_bits(gh: str) -> Tuple[int, int, int, int]:
    """Decode *gh* into ``(lat_index, lat_bits, lon_index, lon_bits)``."""
    lat_index = lon_index = 0
    lat_bits = lon_bits = 0
    for position, char in enumerate(gh):
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError(f"invalid geohash character: {char!r}") from None
        for offset, shift in enumerate((4, 3, 2, 1, 0)):
            bit = (value >> shift) & 1
            if (position * 5 + offset) % 2 == 0:
                lon_index = (lon_index << 1) | bit
                lon_bits += 1
            else:
                lat_index = (lat_index << 1) | bit
                lat_bits += 1
    return lat_index, lat_bits, lon_index, lon_bits


def _join_bits(lat_index: int, lat_bits: int, lon_index: int, lon_bits: int) -> str:
    """Re-interleave a ``(row, column)`` address back into a geohash string."""
    chars: List[str] = []
    value = 0
    filled = 0
    for position in range(lat_bits + lon_bits):
        half = position // 2
        if position % 2 == 0:
            bit = (lon_index >> (lon_bits - 1 - half)) & 1
        else:
            bit = (lat_index >> (lat_bits - 1 - half)) & 1
        value = (value << 1) | bit
        filled += 1
        if filled == 5:
            chars.append(_BASE32[value])
            value = 0
            filled = 0
    return "".join(chars)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes surrounding cell *gh*, at the same precision.

    The result is an unordered list of the up-to-8 adjacent cells. East/west
    neighbours wrap across the antimeridian; neighbours that would lie beyond a
    pole do not exist and are omitted, so a cell touching a pole yields 5
    neighbours. Returned geohashes are lowercase.

    Raises:
        TypeError: if *gh* is not a string.
        ValueError: if *gh* is empty or contains a non-base32 character.
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a str, got {type(gh).__name__}")
    key = gh.lower()
    if not key:
        raise ValueError("geohash must be a non-empty string")

    lat_index, lat_bits, lon_index, lon_bits = _split_bits(key)
    rows = 1 << lat_bits
    columns = 1 << lon_bits

    neighbors: List[str] = []
    seen = set()
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            row = lat_index + dlat
            if not 0 <= row < rows:
                continue  # beyond a pole: no such cell
            column = (lon_index + dlon) % columns  # wraps the antimeridian
            neighbor = _join_bits(row, lat_bits, column, lon_bits)
            if neighbor not in seen:
                seen.add(neighbor)
                neighbors.append(neighbor)
    return neighbors