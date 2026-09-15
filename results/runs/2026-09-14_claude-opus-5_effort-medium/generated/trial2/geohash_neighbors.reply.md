```python
"""Geohash neighbour computation.

Provides :func:`geohash_neighbors`, which returns the geohashes of the eight
cells surrounding a given geohash cell, at the same precision.  East/west
neighbours wrap across the antimeridian; neighbours that would lie beyond the
poles do not exist and are omitted, so cells in the top or bottom row have
fewer than eight neighbours.

Only the standard library is used, and importing this module has no side
effects.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors", "encode", "decode_exactly"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}


def _normalize(gh: str) -> str:
    """Validate ``gh`` and return it as a lowercase geohash string."""
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string")
    cleaned = gh.strip().lower()
    if not cleaned:
        raise ValueError("geohash must be a non-empty string")
    for ch in cleaned:
        if ch not in _DECODE_MAP:
            raise ValueError(f"invalid geohash character: {ch!r}")
    return cleaned


def decode_exactly(gh: str) -> tuple[float, float, float, float]:
    """Decode ``gh`` to ``(lat, lon, lat_err, lon_err)``.

    ``lat``/``lon`` are the cell centre and the errors are half the cell
    height/width, so the cell spans ``lat +/- lat_err`` by ``lon +/- lon_err``.

    All the arithmetic is repeated halving of 180 and 360, which is exact in
    binary floating point, so the returned bounds are exact cell boundaries.
    """
    gh = _normalize(gh)

    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    is_lon = True

    for ch in gh:
        value = _DECODE_MAP[ch]
        for mask in (16, 8, 4, 2, 1):
            bit = value & mask
            if is_lon:
                mid = (lon_lo + lon_hi) / 2
                if bit:
                    lon_lo = mid
                else:
                    lon_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if bit:
                    lat_lo = mid
                else:
                    lat_hi = mid
            is_lon = not is_lon

    return (
        (lat_lo + lat_hi) / 2,
        (lon_lo + lon_hi) / 2,
        (lat_hi - lat_lo) / 2,
        (lon_hi - lon_lo) / 2,
    )


def encode(lat: float, lon: float, precision: int) -> str:
    """Encode ``(lat, lon)`` to a geohash of ``precision`` characters."""
    if precision < 1:
        raise ValueError("precision must be at least 1")

    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    is_lon = True

    chars: list[str] = []
    bits = 0
    nbits = 0

    while len(chars) < precision:
        if is_lon:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                bits = (bits << 1) | 1
                lon_lo = mid
            else:
                bits <<= 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                bits = (bits << 1) | 1
                lat_lo = mid
            else:
                bits <<= 1
                lat_hi = mid
        is_lon = not is_lon

        nbits += 1
        if nbits == 5:
            chars.append(_BASE32[bits])
            bits = 0
            nbits = 0

    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding ``gh``.

    The result contains up to eight geohashes of the same precision as ``gh``,
    in no particular order.  Longitude wraps across the antimeridian; the two
    or three neighbours that would lie beyond a pole are omitted, so a cell
    touching a pole has fewer than eight neighbours.
    """
    gh = _normalize(gh)
    precision = len(gh)
    lat, lon, lat_err, lon_err = decode_exactly(gh)

    cell_height = 2 * lat_err
    cell_width = 2 * lon_err

    neighbors: list[str] = []
    seen = {gh}

    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue

            nlat = lat + dlat * cell_height
            if not -90.0 <= nlat <= 90.0:
                # Beyond a pole: no such cell.
                continue

            nlon = lon + dlon * cell_width
            # Wrap across the antimeridian into [-180, 180).
            nlon = ((nlon + 180.0) % 360.0) - 180.0

            code = encode(nlat, nlon, precision)
            if code not in seen:
                seen.add(code)
                neighbors.append(code)

    return neighbors
```