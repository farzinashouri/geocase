```python
"""Geohash neighbour computation.

Provides ``geohash_neighbors(gh)``, which returns the geohashes of the up to
eight cells surrounding ``gh`` at the same precision. East/west neighbours
wrap across the antimeridian; cells that would lie beyond a pole are omitted.
"""

from __future__ import annotations

from typing import List, Tuple

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}


def _decode_bounds(gh: str) -> Tuple[float, float, float, float]:
    """Return (lat_lo, lat_hi, lon_lo, lon_hi) for the cell ``gh``."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    even = True  # geohash bits alternate lon, lat, lon, ...
    for ch in gh:
        try:
            val = _DECODE[ch]
        except KeyError:
            raise ValueError(f"invalid geohash character {ch!r} in {gh!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (val >> shift) & 1
            if even:
                mid = (lon_lo + lon_hi) / 2.0
                if bit:
                    lon_lo = mid
                else:
                    lon_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2.0
                if bit:
                    lat_lo = mid
                else:
                    lat_hi = mid
            even = not even
    return lat_lo, lat_hi, lon_lo, lon_hi


def _encode(lat: float, lon: float, precision: int) -> str:
    """Encode a point to a geohash of ``precision`` characters."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    even = True
    out: List[str] = []
    val = 0
    nbits = 0
    while len(out) < precision:
        if even:
            mid = (lon_lo + lon_hi) / 2.0
            if lon >= mid:
                val = (val << 1) | 1
                lon_lo = mid
            else:
                val <<= 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2.0
            if lat >= mid:
                val = (val << 1) | 1
                lat_lo = mid
            else:
                val <<= 1
                lat_hi = mid
        even = not even
        nbits += 1
        if nbits == 5:
            out.append(_BASE32[val])
            val = 0
            nbits = 0
    return "".join(out)


def geohash_neighbors(gh: str) -> List[str]:
    """Return the geohashes of the cells surrounding ``gh`` (same precision).

    Up to eight neighbours are returned, in no particular order. East and
    west neighbours wrap across the antimeridian. Neighbours that would lie
    beyond the north or south pole do not exist and are omitted.
    """
    if not isinstance(gh, str) or not gh:
        raise ValueError("geohash must be a non-empty string")
    gh = gh.lower()
    precision = len(gh)

    lat_lo, lat_hi, lon_lo, lon_hi = _decode_bounds(gh)
    lat_step = lat_hi - lat_lo
    lon_step = lon_hi - lon_lo
    clat = (lat_lo + lat_hi) / 2.0
    clon = (lon_lo + lon_hi) / 2.0

    result: List[str] = []
    for dlat in (-1, 0, 1):
        nlat = clat + dlat * lat_step
        if nlat <= -90.0 or nlat >= 90.0:
            continue  # beyond a pole: no such cell
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            nlon = clon + dlon * lon_step
            if nlon >= 180.0:
                nlon -= 360.0
            elif nlon < -180.0:
                nlon += 360.0
            result.append(_encode(nlat, nlon, precision))
    return result


__all__ = ["geohash_neighbors"]
```