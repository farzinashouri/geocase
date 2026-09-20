```python
"""Geohash neighbour computation.

Pure standard-library implementation. A geohash is decoded to a pair of
integer cell indices (longitude column, latitude row) at the hash's bit
precision; the eight surrounding cells are obtained by stepping those
indices and re-encoding. East/west steps wrap modulo the number of
longitude columns (antimeridian). North/south steps that leave the valid
row range (beyond a pole) are dropped.
"""

from __future__ import annotations

from typing import List, Tuple

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode_to_indices(gh: str) -> Tuple[int, int, int, int]:
    """Return (lon_index, lat_index, lon_bits, lat_bits) for a geohash.

    Geohash bits alternate longitude, latitude, longitude, ... starting
    with longitude, so a hash of n characters has ceil(5n/2) longitude
    bits and floor(5n/2) latitude bits.
    """
    lon = lat = 0
    lon_bits = lat_bits = 0
    is_lon = True
    for ch in gh:
        try:
            value = _DECODE[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character: {ch!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if is_lon:
                lon = (lon << 1) | bit
                lon_bits += 1
            else:
                lat = (lat << 1) | bit
                lat_bits += 1
            is_lon = not is_lon
    return lon, lat, lon_bits, lat_bits


def _encode_from_indices(lon: int, lat: int, lon_bits: int, lat_bits: int) -> str:
    """Inverse of _decode_to_indices: interleave the index bits into base32."""
    total = lon_bits + lat_bits
    bits = 0
    lon_shift = lon_bits - 1
    lat_shift = lat_bits - 1
    for i in range(total):
        if i % 2 == 0:
            bit = (lon >> lon_shift) & 1
            lon_shift -= 1
        else:
            bit = (lat >> lat_shift) & 1
            lat_shift -= 1
        bits = (bits << 1) | bit
    chars = []
    for i in range(total // 5):
        shift = total - 5 * (i + 1)
        chars.append(_BASE32[(bits >> shift) & 31])
    return "".join(chars)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the up-to-8 cells surrounding ``gh``.

    All results have the same precision (length) as ``gh``. East and west
    neighbours wrap across the antimeridian. Cells that would lie beyond
    the north or south pole do not exist and are omitted, so a cell that
    touches a pole has 5 neighbours instead of 8.

    Raises ValueError for characters outside the geohash alphabet.
    An empty string has no neighbours and yields an empty list.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a str")
    gh = gh.strip().lower()
    if not gh:
        return []

    lon, lat, lon_bits, lat_bits = _decode_to_indices(gh)
    lon_cells = 1 << lon_bits
    lat_cells = 1 << lat_bits

    neighbors: List[str] = []
    for dlat in (1, 0, -1):
        new_lat = lat + dlat
        if new_lat < 0 or new_lat >= lat_cells:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            new_lon = (lon + dlon) % lon_cells  # antimeridian wrap
            neighbors.append(_encode_from_indices(new_lon, new_lat, lon_bits, lat_bits))
    return neighbors
```