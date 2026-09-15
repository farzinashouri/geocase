"""Neighbouring cells of a geohash.

A geohash string encodes an interleaved pair of binary subdivisions: the
first bit halves the longitude range, the second halves the latitude range,
and so on, five bits per base-32 character.  Decoding a geohash back into
that pair of integer grid indices makes the neighbourhood trivial -- the
eight surrounding cells are the index offsets (+-1, +-1), with longitude
taken modulo the grid width (the antimeridian wrap) and latitude simply
dropped when it leaves the grid (cells past a pole do not exist).

Standard library only; importing this module has no side effects.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {char: value for value, char in enumerate(_BASE32)}


def _decode_cell(geohash: str) -> tuple[int, int, int, int]:
    """Return ``(lat_index, lon_index, lat_bits, lon_bits)`` for *geohash*.

    The indices address the cell in the regular ``2**lat_bits`` by
    ``2**lon_bits`` grid at this precision, counting from the south-west
    corner of the world.
    """
    lat_index = lon_index = 0
    lat_bits = lon_bits = 0
    is_lon = True  # the very first bit of a geohash splits longitude
    for char in geohash:
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError(f"not a valid geohash character: {char!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if is_lon:
                lon_index = (lon_index << 1) | bit
                lon_bits += 1
            else:
                lat_index = (lat_index << 1) | bit
                lat_bits += 1
            is_lon = not is_lon
    return lat_index, lon_index, lat_bits, lon_bits


def _encode_cell(lat_index: int, lon_index: int, lat_bits: int, lon_bits: int) -> str:
    """Inverse of :func:`_decode_cell`: re-interleave grid indices into base 32."""
    chars = []
    accumulator = 0
    filled = 0
    for position in range(lat_bits + lon_bits):
        half = position // 2
        if position % 2 == 0:
            bit = (lon_index >> (lon_bits - 1 - half)) & 1
        else:
            bit = (lat_index >> (lat_bits - 1 - half)) & 1
        accumulator = (accumulator << 1) | bit
        filled += 1
        if filled == 5:
            chars.append(_BASE32[accumulator])
            accumulator = 0
            filled = 0
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding ``gh``.

    The result holds the neighbouring cells at the same precision as ``gh``,
    in no particular order, lower-cased.  East/west neighbours wrap across the
    antimeridian, so a cell against the +-180 meridian still has all eight.
    Latitude does not wrap: a cell in the top or bottom row touches a pole and
    has nothing beyond it, so it yields five neighbours instead of eight.

    >>> sorted(geohash_neighbors("s"))
    ['7', 'e', 'g', 'k', 'm', 't', 'u', 'v']
    >>> len(geohash_neighbors("b"))  # 'b' is in the northernmost row
    5
    >>> "z" in geohash_neighbors("b")  # ... and wraps west to the far side
    True

    :raises TypeError: if ``gh`` is not a string.
    :raises ValueError: if ``gh`` is empty or holds a non-base-32 character.
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a str, got {type(gh).__name__}")
    geohash = gh.lower()
    if not geohash:
        raise ValueError("geohash must not be empty")

    lat_index, lon_index, lat_bits, lon_bits = _decode_cell(geohash)
    lat_cells = 1 << lat_bits
    lon_cells = 1 << lon_bits

    neighbors = []
    for dlat in (1, 0, -1):
        lat = lat_index + dlat
        if not 0 <= lat < lat_cells:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue  # the cell itself
            lon = (lon_index + dlon) % lon_cells  # wraps the antimeridian
            neighbors.append(_encode_cell(lat, lon, lat_bits, lon_bits))
    return neighbors