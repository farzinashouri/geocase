```python
"""Geohash neighbour computation using only the standard library.

A geohash of precision ``n`` encodes ``5 * n`` bits, alternating longitude
and latitude bits starting with longitude.  The cell therefore has an
integer longitude index in ``[0, 2**lon_bits)`` and an integer latitude
index in ``[0, 2**lat_bits)``.  Neighbours are found by shifting these
indices: longitude wraps modulo ``2**lon_bits`` (antimeridian), latitude is
clipped (cells beyond the poles do not exist).
"""

from __future__ import annotations

from typing import List, Tuple

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _to_indices(gh: str) -> Tuple[int, int, int, int]:
    """Return (lon_idx, lat_idx, lon_bits, lat_bits) for a geohash."""
    lon_idx = 0
    lat_idx = 0
    is_lon = True
    for c in gh:
        try:
            v = _DECODE[c]
        except KeyError:
            raise ValueError(f"invalid geohash character: {c!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (v >> shift) & 1
            if is_lon:
                lon_idx = (lon_idx << 1) | bit
            else:
                lat_idx = (lat_idx << 1) | bit
            is_lon = not is_lon
    total = 5 * len(gh)
    lon_bits = (total + 1) // 2
    lat_bits = total // 2
    return lon_idx, lat_idx, lon_bits, lat_bits


def _from_indices(lon_idx: int, lat_idx: int, lon_bits: int, lat_bits: int) -> str:
    """Rebuild a geohash string from cell indices and bit counts."""
    total = lon_bits + lat_bits
    combined = 0
    is_lon = True
    li = lon_bits - 1
    la = lat_bits - 1
    for _ in range(total):
        if is_lon:
            bit = (lon_idx >> li) & 1
            li -= 1
        else:
            bit = (lat_idx >> la) & 1
            la -= 1
        combined = (combined << 1) | bit
        is_lon = not is_lon
    chars = []
    for i in range(total // 5):
        shift = total - 5 * (i + 1)
        chars.append(_BASE32[(combined >> shift) & 31])
    return "".join(chars)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the cells surrounding ``gh`` at the same precision.

    East/west neighbours wrap across the antimeridian.  Cells that would lie
    beyond the north or south pole are omitted, so a cell touching a pole
    returns fewer than 8 neighbours.  Order of the result is unspecified.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string")
    gh = gh.strip().lower()
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    lon_idx, lat_idx, lon_bits, lat_bits = _to_indices(gh)
    lon_cells = 1 << lon_bits
    lat_cells = 1 << lat_bits

    result: List[str] = []
    for dlat in (-1, 0, 1):
        new_lat = lat_idx + dlat
        if new_lat < 0 or new_lat >= lat_cells:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue  # the cell itself
            new_lon = (lon_idx + dlon) % lon_cells  # wrap at antimeridian
            result.append(_from_indices(new_lon, new_lat, lon_bits, lat_bits))
    return result


__all__ = ["geohash_neighbors"]
```