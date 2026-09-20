```python
"""Geohash neighbour computation.

Pure standard library; importing this module has no side effects.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors", "geohash_decode_bbox", "geohash_encode"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}


def geohash_decode_bbox(gh: str) -> tuple[float, float, float, float]:
    """Return (lat_min, lat_max, lon_min, lon_max) for a geohash cell."""
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string")
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True

    for ch in gh:
        try:
            val = _DECODE_MAP[ch.lower()]
        except KeyError:
            raise ValueError(f"invalid geohash character: {ch!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (val >> shift) & 1
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

    return lat_min, lat_max, lon_min, lon_max


def geohash_encode(lat: float, lon: float, precision: int) -> str:
    """Encode a latitude/longitude pair to a geohash of the given precision."""
    if precision < 1:
        raise ValueError("precision must be >= 1")

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    is_lon = True
    bit = 0
    val = 0
    out: list[str] = []

    while len(out) < precision:
        if is_lon:
            mid = (lon_min + lon_max) / 2.0
            if lon >= mid:
                val = (val << 1) | 1
                lon_min = mid
            else:
                val = val << 1
                lon_max = mid
        else:
            mid = (lat_min + lat_max) / 2.0
            if lat >= mid:
                val = (val << 1) | 1
                lat_min = mid
            else:
                val = val << 1
                lat_max = mid
        is_lon = not is_lon

        bit += 1
        if bit == 5:
            out.append(_BASE32[val])
            bit = 0
            val = 0

    return "".join(out)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding ``gh``.

    The result holds up to 8 geohashes at the same precision as ``gh``.
    East/west neighbours wrap across the antimeridian; neighbours that would
    lie beyond a pole do not exist and are omitted, so a cell touching a pole
    has fewer than 8 neighbours.
    """
    lat_min, lat_max, lon_min, lon_max = geohash_decode_bbox(gh)
    precision = len(gh)

    lat_c = (lat_min + lat_max) / 2.0
    lon_c = (lon_min + lon_max) / 2.0
    lat_step = lat_max - lat_min
    lon_step = lon_max - lon_min

    self_gh = geohash_encode(lat_c, lon_c, precision)
    neighbors: list[str] = []

    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            lat = lat_c + dlat * lat_step
            if lat > 90.0 or lat < -90.0:
                continue  # beyond a pole: no such cell
            lon = lon_c + dlon * lon_step
            # Wrap longitude across the antimeridian into [-180, 180).
            lon = ((lon + 180.0) % 360.0) - 180.0
            candidate = geohash_encode(lat, lon, precision)
            if candidate != self_gh and candidate not in neighbors:
                neighbors.append(candidate)

    return neighbors
```