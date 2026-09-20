"""Geohash neighbour computation.

A geohash encodes a latitude/longitude cell as a base-32 string. Each
character contributes 5 bits, and the bits alternate between longitude
and latitude starting with longitude. Decoding a geohash of *n*
characters therefore yields an integer longitude index with
``ceil(5n / 2)`` bits and an integer latitude index with
``floor(5n / 2)`` bits. Neighbouring cells are found by stepping those
indices by one and re-encoding: longitude wraps around the antimeridian,
latitude steps that leave the valid range fall off a pole and are
dropped.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode_indices(gh: str) -> tuple[int, int, int, int]:
    """Return (lon_idx, lat_idx, lon_bits, lat_bits) for a geohash."""
    lon_idx = 0
    lat_idx = 0
    lon_bits = 0
    lat_bits = 0
    is_lon = True
    for ch in gh:
        value = _DECODE[ch]
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if is_lon:
                lon_idx = (lon_idx << 1) | bit
                lon_bits += 1
            else:
                lat_idx = (lat_idx << 1) | bit
                lat_bits += 1
            is_lon = not is_lon
    return lon_idx, lat_idx, lon_bits, lat_bits


def _encode_indices(lon_idx: int, lat_idx: int, lon_bits: int, lat_bits: int) -> str:
    """Interleave longitude/latitude indices back into a geohash string."""
    total_bits = lon_bits + lat_bits
    combined = 0
    lon_pos = lon_bits - 1
    lat_pos = lat_bits - 1
    is_lon = True
    for _ in range(total_bits):
        if is_lon:
            bit = (lon_idx >> lon_pos) & 1
            lon_pos -= 1
        else:
            bit = (lat_idx >> lat_pos) & 1
            lat_pos -= 1
        combined = (combined << 1) | bit
        is_lon = not is_lon

    chars = []
    for i in range(total_bits // 5):
        shift = total_bits - 5 * (i + 1)
        chars.append(_BASE32[(combined >> shift) & 0x1F])
    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the up-to-8 cells surrounding ``gh``.

    The result has the same precision as ``gh``. East and west neighbours
    wrap across the antimeridian. Cells that would lie beyond the north
    or south pole do not exist and are omitted, so a cell touching a pole
    returns fewer than 8 neighbours. Order of the returned list is
    unspecified.

    Raises:
        TypeError: if ``gh`` is not a string.
        ValueError: if ``gh`` is empty or contains non-geohash characters.
    """
    if not isinstance(gh, str):
        raise TypeError(f"geohash must be a str, got {type(gh).__name__}")
    gh = gh.lower()
    if not gh:
        raise ValueError("geohash must not be empty")
    bad = [c for c in gh if c not in _DECODE]
    if bad:
        raise ValueError(f"invalid geohash character(s): {''.join(sorted(set(bad)))!r}")

    lon_idx, lat_idx, lon_bits, lat_bits = _decode_indices(gh)
    lon_cells = 1 << lon_bits
    lat_cells = 1 << lat_bits

    neighbours: list[str] = []
    for dlat in (-1, 0, 1):
        new_lat = lat_idx + dlat
        if new_lat < 0 or new_lat >= lat_cells:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue  # the cell itself
            new_lon = (lon_idx + dlon) % lon_cells  # wrap across antimeridian
            neighbours.append(_encode_indices(new_lon, new_lat, lon_bits, lat_bits))

    # With a 1-bit longitude axis (never the case for real precisions, but
    # cheap to guard) east and west would coincide; dedupe preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for n in neighbours:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique