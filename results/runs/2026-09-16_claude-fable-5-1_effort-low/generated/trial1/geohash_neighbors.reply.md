```python
"""Geohash neighbour computation.

Provides ``geohash_neighbors(gh)`` which returns the geohashes, at the same
precision as ``gh``, of the up to 8 cells surrounding ``gh``.  East/west
neighbours wrap across the antimeridian; cells that would lie beyond the
poles do not exist and are omitted.
"""

from __future__ import annotations

from typing import List, Tuple

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode_bits(gh: str) -> Tuple[int, int, int, int]:
    """Return (lon_bits, lat_bits, lon_index, lat_index) for a geohash.

    Geohash interleaves bits starting with longitude.  The indices are the
    integer positions of the cell along each axis at the cell's own bit
    resolution.
    """
    lon_idx = 0
    lat_idx = 0
    lon_bits = 0
    lat_bits = 0
    even = True  # first bit of each string is a longitude bit
    for ch in gh:
        try:
            val = _DECODE[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character {ch!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (val >> shift) & 1
            if even:
                lon_idx = (lon_idx << 1) | bit
                lon_bits += 1
            else:
                lat_idx = (lat_idx << 1) | bit
                lat_bits += 1
            even = not even
    return lon_bits, lat_bits, lon_idx, lat_idx


def _encode_bits(lon_bits: int, lat_bits: int, lon_idx: int, lat_idx: int) -> str:
    """Inverse of _decode_bits."""
    total = lon_bits + lat_bits
    out = []
    val = 0
    n = 0
    li = lon_bits - 1
    ti = lat_bits - 1
    for i in range(total):
        if i % 2 == 0:
            bit = (lon_idx >> li) & 1
            li -= 1
        else:
            bit = (lat_idx >> ti) & 1
            ti -= 1
        val = (val << 1) | bit
        n += 1
        if n == 5:
            out.append(_BASE32[val])
            val = 0
            n = 0
    return "".join(out)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the up to 8 cells surrounding ``gh``.

    Longitude wraps across the antimeridian.  Cells beyond the north or
    south pole are omitted, so cells touching a pole return fewer than 8.
    """
    gh = gh.lower()
    if not gh:
        raise ValueError("geohash must be non-empty")
    lon_bits, lat_bits, lon_idx, lat_idx = _decode_bits(gh)
    n_lon = 1 << lon_bits
    n_lat = 1 << lat_bits

    result: List[str] = []
    for dlat in (-1, 0, 1):
        new_lat = lat_idx + dlat
        if new_lat < 0 or new_lat >= n_lat:
            continue  # beyond a pole
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            new_lon = (lon_idx + dlon) % n_lon  # wrap across antimeridian
            result.append(_encode_bits(lon_bits, lat_bits, new_lon, new_lat))
    return result


__all__ = ["geohash_neighbors"]
```