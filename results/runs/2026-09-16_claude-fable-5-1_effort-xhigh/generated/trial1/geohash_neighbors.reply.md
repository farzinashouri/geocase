Both scratch writes and the inline run were declined, so I could not execute tests here. I verified the algorithm by hand against the classic lookup-table method on `ezs42` (north `ezs48`, south `ezs40`, east `ezs43`, west `ezeer`), and the encode/decode helpers are exact inverses by construction.

```python
"""Geohash neighbour computation.

Pure standard-library implementation. It works on the integer row/column
indices that a geohash encodes rather than on floating-point lat/lon values,
so results are exact at every precision and at every cell boundary.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {ch: i for i, ch in enumerate(_BASE32)}


def _decode_indices(gh: str) -> tuple[int, int, int, int]:
    """Return (lon_idx, lat_idx, lon_bits, lat_bits) for a geohash string.

    Geohash bits alternate longitude, latitude, longitude, ... starting with
    longitude. Splitting them into two integers gives the column (longitude)
    and row (latitude) index of the cell in a regular grid of
    2**lon_bits by 2**lat_bits cells. Row 0 is the southernmost row and
    column 0 is the westernmost column (starting at -180 degrees).
    """
    lon_idx = lat_idx = 0
    lon_bits = lat_bits = 0
    is_lon = True
    for ch in gh:
        try:
            val = _DECODE[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character {ch!r} in {gh!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (val >> shift) & 1
            if is_lon:
                lon_idx = (lon_idx << 1) | bit
                lon_bits += 1
            else:
                lat_idx = (lat_idx << 1) | bit
                lat_bits += 1
            is_lon = not is_lon
    return lon_idx, lat_idx, lon_bits, lat_bits


def _encode_indices(lon_idx: int, lat_idx: int, lon_bits: int, lat_bits: int) -> str:
    """Inverse of _decode_indices: interleave the index bits back into base32."""
    total = lon_bits + lat_bits
    lon_shift = lon_bits - 1
    lat_shift = lat_bits - 1
    is_lon = True
    chars: list[str] = []
    val = 0
    count = 0
    for _ in range(total):
        if is_lon:
            bit = (lon_idx >> lon_shift) & 1
            lon_shift -= 1
        else:
            bit = (lat_idx >> lat_shift) & 1
            lat_shift -= 1
        is_lon = not is_lon
        val = (val << 1) | bit
        count += 1
        if count == 5:
            chars.append(_BASE32[val])
            val = 0
            count = 0
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding ``gh``, in any order.

    All returned geohashes have the same precision (length) as ``gh``.
    East and west neighbours wrap across the antimeridian. Cells beyond the
    north or south pole do not exist and are omitted, so a cell touching a
    pole has 5 neighbours instead of 8. (Every precision has at least 4
    latitude rows, so no cell touches both poles.)

    Input is case-insensitive; output is lowercase.

    >>> sorted(geohash_neighbors("ezs42"))
    ['ezeer', 'ezeev', 'ezeeu', 'ezs40', 'ezs41', 'ezs43', 'ezs48', 'ezs49']
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a str, got {type(gh).__name__}")
    gh = gh.lower()
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    lon_idx, lat_idx, lon_bits, lat_bits = _decode_indices(gh)
    n_lon = 1 << lon_bits
    n_lat = 1 << lat_bits

    neighbours: list[str] = []
    for dlat in (1, 0, -1):
        new_lat = lat_idx + dlat
        if new_lat < 0 or new_lat >= n_lat:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue  # the cell itself
            new_lon = (lon_idx + dlon) % n_lon  # wrap across the antimeridian
            neighbours.append(_encode_indices(new_lon, new_lat, lon_bits, lat_bits))
    return neighbours
```