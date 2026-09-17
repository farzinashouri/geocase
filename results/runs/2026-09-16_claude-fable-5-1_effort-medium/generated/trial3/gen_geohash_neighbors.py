"""Geohash neighbour computation.

Implements ``geohash_neighbors(gh)``: given a geohash string, return the
geohashes (same precision) of the up-to-8 surrounding cells. East/west
neighbours wrap across the antimeridian; north/south neighbours that would
lie beyond a pole are omitted.

The approach decodes the geohash into its interleaved longitude and latitude
bit-indices, offsets those integer indices by -1/0/+1, and re-encodes. This
avoids floating-point decode/encode round-trips entirely.
"""

from __future__ import annotations

from typing import List, Tuple

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _bit_counts(length: int) -> Tuple[int, int]:
    """Return (lon_bits, lat_bits) for a geohash of ``length`` characters."""
    total = 5 * length
    # Interleaving starts with a longitude bit, so longitude gets the extra
    # bit when the total is odd.
    return (total + 1) // 2, total // 2


def _split(gh: str) -> Tuple[int, int]:
    """Decode a geohash into integer (lon_index, lat_index) cell coordinates."""
    total = 5 * len(gh)
    bits = 0
    for c in gh:
        bits = (bits << 5) | _DECODE[c]
    lon = 0
    lat = 0
    for i in range(total):
        b = (bits >> (total - 1 - i)) & 1
        if i % 2 == 0:
            lon = (lon << 1) | b
        else:
            lat = (lat << 1) | b
    return lon, lat


def _join(lon: int, lat: int, length: int) -> str:
    """Encode integer (lon_index, lat_index) coordinates into a geohash."""
    total = 5 * length
    lon_bits, lat_bits = _bit_counts(length)
    bits = 0
    li = lon_bits - 1
    ai = lat_bits - 1
    for i in range(total):
        if i % 2 == 0:
            b = (lon >> li) & 1
            li -= 1
        else:
            b = (lat >> ai) & 1
            ai -= 1
        bits = (bits << 1) | b
    return "".join(
        _BASE32[(bits >> (5 * (length - 1 - k))) & 31] for k in range(length)
    )


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the cells surrounding ``gh`` at the same precision.

    East and west neighbours wrap across the antimeridian. Cells that would
    lie beyond the north or south pole do not exist and are omitted, so a
    cell touching a pole returns 5 neighbours instead of 8.

    Raises:
        TypeError: if ``gh`` is not a string.
        ValueError: if ``gh`` is empty or contains characters outside the
            geohash base-32 alphabet (case-insensitive).
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a str, got {type(gh).__name__}")
    if not gh:
        raise ValueError("geohash must be non-empty")
    gh = gh.lower()
    bad = [c for c in gh if c not in _DECODE]
    if bad:
        raise ValueError(f"invalid geohash character(s): {bad!r}")

    length = len(gh)
    lon_bits, lat_bits = _bit_counts(length)
    lon_cells = 1 << lon_bits
    lat_cells = 1 << lat_bits

    lon, lat = _split(gh)

    out: List[str] = []
    for dlat in (-1, 0, 1):
        nlat = lat + dlat
        if nlat < 0 or nlat >= lat_cells:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            nlon = (lon + dlon) % lon_cells  # wrap across the antimeridian
            out.append(_join(nlon, nlat, length))
    return out