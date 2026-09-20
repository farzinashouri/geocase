```python
"""Geohash neighbour computation.

`geohash_neighbors(gh)` returns the geohashes, at the same precision as
`gh`, of the up to 8 cells surrounding the cell encoded by `gh`.

East/west neighbours wrap across the antimeridian. Cells that would lie
beyond the north or south pole do not exist and are omitted.
"""

from __future__ import annotations

from typing import List, Tuple

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode_to_cells(gh: str) -> Tuple[int, int, int, int]:
    """Decode a geohash into integer cell indices.

    Returns (lon_idx, lat_idx, lon_bits, lat_bits) where lon_idx is in
    [0, 2**lon_bits) and lat_idx is in [0, 2**lat_bits).
    """
    lon_idx = 0
    lat_idx = 0
    lon_bits = 0
    lat_bits = 0
    even = True  # geohash starts with a longitude bit
    for ch in gh:
        try:
            val = _DECODE[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character: {ch!r}") from None
        for shift in range(4, -1, -1):
            bit = (val >> shift) & 1
            if even:
                lon_idx = (lon_idx << 1) | bit
                lon_bits += 1
            else:
                lat_idx = (lat_idx << 1) | bit
                lat_bits += 1
            even = not even
    return lon_idx, lat_idx, lon_bits, lat_bits


def _encode_from_cells(lon_idx: int, lat_idx: int, lon_bits: int, lat_bits: int) -> str:
    """Inverse of `_decode_to_cells`."""
    total_bits = lon_bits + lat_bits
    bits: List[int] = []
    li, la = lon_bits - 1, lat_bits - 1
    even = True
    for _ in range(total_bits):
        if even:
            bits.append((lon_idx >> li) & 1)
            li -= 1
        else:
            bits.append((lat_idx >> la) & 1)
            la -= 1
        even = not even
    out = []
    for i in range(0, total_bits, 5):
        chunk = bits[i:i + 5]
        val = 0
        for b in chunk:
            val = (val << 1) | b
        out.append(_BASE32[val])
    return "".join(out)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the cells surrounding `gh`.

    The result has 8 entries for interior cells, and fewer for cells that
    touch the north or south pole. East/west neighbours wrap across the
    antimeridian. Order is unspecified.
    """
    if not isinstance(gh, str) or not gh:
        raise ValueError("geohash must be a non-empty string")
    gh = gh.lower()
    lon_idx, lat_idx, lon_bits, lat_bits = _decode_to_cells(gh)
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
            result.append(_encode_from_cells(new_lon, new_lat, lon_bits, lat_bits))
    return result


__all__ = ["geohash_neighbors"]
```