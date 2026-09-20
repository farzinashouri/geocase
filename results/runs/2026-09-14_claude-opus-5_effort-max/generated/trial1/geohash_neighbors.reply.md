```python
"""Neighbour lookup for geohash cells.

A geohash is a base-32 encoding of interleaved longitude/latitude bits: the
first bit -- and every other bit after it -- refines longitude, the remaining
bits refine latitude.  An ``n``-character geohash therefore carries
``ceil(5n/2)`` longitude bits and ``floor(5n/2)`` latitude bits, which is
precisely a cell index into a ``2**lat_bits`` by ``2**lon_bits`` grid covering
the globe.

Neighbour lookup is done on those integer indices rather than on decoded cell
centres, so it is exact: no floating-point drift across cell boundaries, and
the antimeridian wrap is just arithmetic modulo the column count.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _to_indices(gh: str) -> tuple[int, int, int, int]:
    """Split a geohash into ``(lat_index, lon_index, lat_bits, lon_bits)``."""
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a str, got {type(gh).__name__}")
    gh = gh.lower()
    if not gh:
        raise ValueError("geohash must not be empty")

    lat = lon = 0
    lat_bits = lon_bits = 0
    is_lon = True
    for char in gh:
        try:
            value = _DECODE[char]
        except KeyError:
            raise ValueError(f"invalid geohash character: {char!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if is_lon:
                lon = (lon << 1) | bit
                lon_bits += 1
            else:
                lat = (lat << 1) | bit
                lat_bits += 1
            is_lon = not is_lon
    return lat, lon, lat_bits, lon_bits


def _to_geohash(lat: int, lon: int, lat_bits: int, lon_bits: int) -> str:
    """Re-interleave grid indices back into a geohash string."""
    chars = []
    is_lon = True
    lat_taken = lon_taken = 0
    accumulator = held = 0
    for _ in range(lat_bits + lon_bits):
        if is_lon:
            bit = (lon >> (lon_bits - 1 - lon_taken)) & 1
            lon_taken += 1
        else:
            bit = (lat >> (lat_bits - 1 - lat_taken)) & 1
            lat_taken += 1
        is_lon = not is_lon

        accumulator = (accumulator << 1) | bit
        held += 1
        if held == 5:
            chars.append(_BASE32[accumulator])
            accumulator = held = 0
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding ``gh``.

    All results share the precision of ``gh``.  East/west neighbours wrap
    across the antimeridian, so every cell has both.  North/south neighbours
    beyond a pole do not exist and are omitted, so a cell in the top or bottom
    row of the grid has five neighbours rather than eight.

    Args:
        gh: A geohash string (case-insensitive; results are lowercase).

    Returns:
        A list of up to eight distinct geohashes, in unspecified order.

    Raises:
        TypeError: If ``gh`` is not a string.
        ValueError: If ``gh`` is empty or contains a non-base-32 character.
    """
    lat, lon, lat_bits, lon_bits = _to_indices(gh)
    lat_rows = 1 << lat_bits
    lon_cols = 1 << lon_bits

    neighbors = []
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            neighbor_lat = lat + dlat
            if not 0 <= neighbor_lat < lat_rows:
                continue  # past a pole -- no such cell
            neighbor_lon = (lon + dlon) % lon_cols  # wraps at the antimeridian
            neighbors.append(
                _to_geohash(neighbor_lat, neighbor_lon, lat_bits, lon_bits)
            )
    return neighbors
```