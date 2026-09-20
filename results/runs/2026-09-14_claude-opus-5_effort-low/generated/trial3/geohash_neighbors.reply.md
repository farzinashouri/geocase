```python
"""Geohash neighbour computation.

Provides :func:`geohash_neighbors`, which returns the geohashes of the up-to-8
cells surrounding a given cell at the same precision.  East/west neighbours wrap
across the antimeridian; neighbours that would lie beyond a pole do not exist
and are omitted.

Importing this module has no side effects.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors", "encode", "decode_bbox"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}


def decode_bbox(gh: str) -> tuple[float, float, float, float]:
    """Return the bounding box ``(lat_min, lon_min, lat_max, lon_max)`` of *gh*."""
    if not isinstance(gh, str) or not gh:
        raise ValueError("geohash must be a non-empty string")

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True

    for ch in gh.lower():
        try:
            value = _DECODE_MAP[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character: {ch!r}") from None
        for mask in (16, 8, 4, 2, 1):
            bit = 1 if value & mask else 0
            if is_lon:
                mid = (lon_min + lon_max) / 2.0
                if bit:
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2.0
                if bit:
                    lat_min = mid
                else:
                    lat_max = mid
            is_lon = not is_lon

    return lat_min, lon_min, lat_max, lon_max


def encode(lat: float, lon: float, precision: int) -> str:
    """Encode ``(lat, lon)`` as a geohash of the given *precision*."""
    if precision < 1:
        raise ValueError("precision must be >= 1")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("latitude out of range")

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True
    value = 0
    bits = 0
    out = []

    while len(out) < precision:
        if is_lon:
            mid = (lon_min + lon_max) / 2.0
            if lon >= mid:
                value = (value << 1) | 1
                lon_min = mid
            else:
                value <<= 1
                lon_max = mid
        else:
            mid = (lat_min + lat_max) / 2.0
            if lat >= mid:
                value = (value << 1) | 1
                lat_min = mid
            else:
                value <<= 1
                lat_max = mid
        is_lon = not is_lon

        bits += 1
        if bits == 5:
            out.append(_BASE32[value])
            value = 0
            bits = 0

    return "".join(out)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding *gh*, at the same precision.

    The result holds up to 8 geohashes in unspecified order.  East and west
    neighbours wrap across the antimeridian.  Cells that would lie beyond the
    north or south pole do not exist and are omitted, so a cell touching a pole
    has fewer than 8 neighbours.
    """
    lat_min, lon_min, lat_max, lon_max = decode_bbox(gh)
    precision = len(gh)

    # Cell size; both are exact binary fractions of 180/360, so the arithmetic
    # below lands strictly inside the intended neighbouring cells.
    lat_step = lat_max - lat_min
    lon_step = lon_max - lon_min
    lat_c = (lat_min + lat_max) / 2.0
    lon_c = (lon_min + lon_max) / 2.0

    neighbors = []
    seen = set()
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue

            lat = lat_c + dlat * lat_step
            if lat > 90.0 or lat < -90.0:
                continue  # beyond a pole: no such cell

            lon = lon_c + dlon * lon_step
            # Wrap across the antimeridian into [-180, 180).
            lon = ((lon + 180.0) % 360.0) - 180.0

            code = encode(lat, lon, precision)
            if code not in seen:
                seen.add(code)
                neighbors.append(code)

    return neighbors
```