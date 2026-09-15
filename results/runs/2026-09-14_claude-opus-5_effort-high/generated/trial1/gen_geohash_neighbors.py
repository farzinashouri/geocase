"""Geohash neighbour lookup.

Provides :func:`geohash_neighbors`, which returns the geohashes of the eight
cells surrounding a given geohash cell, at the same precision.

East/west neighbours wrap across the antimeridian.  Cells beyond the poles do
not exist, so a cell that touches a pole has fewer than eight neighbours.

Importing this module has no side effects.
"""

from __future__ import annotations

__all__ = ["geohash_neighbors"]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}

_LAT_MIN, _LAT_MAX = -90.0, 90.0
_LON_MIN, _LON_MAX = -180.0, 180.0


def _decode_bbox(gh: str) -> tuple[float, float, float, float]:
    """Return (lat_min, lat_max, lon_min, lon_max) of the cell `gh`."""
    lat_min, lat_max = _LAT_MIN, _LAT_MAX
    lon_min, lon_max = _LON_MIN, _LON_MAX
    is_lon = True  # geohash bits alternate, longitude first

    for char in gh:
        try:
            value = _DECODE_MAP[char]
        except KeyError:
            raise ValueError(f"invalid geohash character: {char!r}") from None
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
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


def _encode(lat: float, lon: float, precision: int) -> str:
    """Encode a point as a geohash of the given precision."""
    lat_min, lat_max = _LAT_MIN, _LAT_MAX
    lon_min, lon_max = _LON_MIN, _LON_MAX
    is_lon = True

    chars = []
    value = 0
    bits = 0
    while len(chars) < precision:
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
            chars.append(_BASE32[value])
            value = 0
            bits = 0

    return "".join(chars)


def geohash_neighbors(gh: str) -> list[str]:
    """Return the geohashes of the cells surrounding `gh`, at its precision.

    The result holds up to eight geohashes, in unspecified order.  Neighbours
    to the east and west wrap around the antimeridian; neighbours that would
    lie beyond a pole are omitted, so a polar cell yields fewer than eight.

    Raises ValueError if `gh` is empty or contains non-base32 characters.
    """
    if not isinstance(gh, str):
        raise TypeError("geohash must be a string")
    gh = gh.strip().lower()
    if not gh:
        raise ValueError("geohash must be a non-empty string")

    precision = len(gh)
    lat_min, lat_max, lon_min, lon_max = _decode_bbox(gh)
    lat_center = (lat_min + lat_max) / 2.0
    lon_center = (lon_min + lon_max) / 2.0
    lat_step = lat_max - lat_min
    lon_step = lon_max - lon_min

    neighbors = []
    for dlat in (1, 0, -1):
        for dlon in (-1, 0, 1):
            if dlat == 0 and dlon == 0:
                continue
            lat = lat_center + dlat * lat_step
            if not (_LAT_MIN < lat < _LAT_MAX):
                continue  # beyond a pole: no such cell
            lon = lon_center + dlon * lon_step
            # wrap across the antimeridian into [-180, 180)
            lon = ((lon + 180.0) % 360.0) - 180.0
            neighbors.append(_encode(lat, lon, precision))

    return neighbors