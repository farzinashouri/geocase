```python
"""Geohash neighbour computation using pure standard-library integer arithmetic.

A geohash interleaves longitude and latitude bits (longitude first) and encodes
them five bits at a time in a base-32 alphabet.  Decoding a geohash of
precision ``p`` yields an integer longitude column and latitude row on a grid
of ``2**ceil(5p/2)`` by ``2**floor(5p/2)`` cells.  Neighbours are then simply
adjacent grid indices: columns wrap around the antimeridian, rows past the
poles do not exist.
"""

from __future__ import annotations

from typing import List, Tuple

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode(gh: str) -> Tuple[int, int, int, int]:
    """Return (lon_idx, lat_idx, lon_bits, lat_bits) for a geohash string."""
    lon_idx = lat_idx = 0
    lon_bits = lat_bits = 0
    even = True  # geohash bit stream starts with a longitude bit
    for ch in gh:
        try:
            value = _DECODE[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character: {ch!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if even:
                lon_idx = (lon_idx << 1) | bit
                lon_bits += 1
            else:
                lat_idx = (lat_idx << 1) | bit
                lat_bits += 1
            even = not even
    return lon_idx, lat_idx, lon_bits, lat_bits


def _encode(lon_idx: int, lat_idx: int, lon_bits: int, lat_bits: int) -> str:
    """Inverse of ``_decode``: interleave the indices back into a geohash."""
    total = lon_bits + lat_bits
    bits = 0
    lon_shift, lat_shift = lon_bits - 1, lat_bits - 1
    even = True
    for _ in range(total):
        if even:
            bit = (lon_idx >> lon_shift) & 1
            lon_shift -= 1
        else:
            bit = (lat_idx >> lat_shift) & 1
            lat_shift -= 1
        bits = (bits << 1) | bit
        even = not even
    chars = []
    for i in range(total // 5):
        shift = total - 5 * (i + 1)
        chars.append(_BASE32[(bits >> shift) & 31])
    return "".join(chars)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the up-to-8 cells surrounding ``gh``.

    The result has the same precision as the input and is lower-case.  East and
    west neighbours wrap across the antimeridian.  Cells that would lie beyond
    the north or south pole are omitted, so a cell touching a pole returns
    fewer than 8 neighbours (5 for a pole-touching cell).

    Raises ``ValueError`` for an empty string or invalid characters.
    """
    if not isinstance(gh, str) or not gh:
        raise ValueError("geohash must be a non-empty string")
    gh = gh.lower()

    lon_idx, lat_idx, lon_bits, lat_bits = _decode(gh)
    n_lon = 1 << lon_bits
    n_lat = 1 << lat_bits

    result: List[str] = []
    for dlat in (1, 0, -1):
        lat = lat_idx + dlat
        if lat < 0 or lat >= n_lat:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            lon = (lon_idx + dlon) % n_lon  # wrap across the antimeridian
            result.append(_encode(lon, lat, lon_bits, lat_bits))
    return result


__all__ = ["geohash_neighbors"]
```