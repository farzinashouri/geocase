"""Split polygons that cross the antimeridian into antimeridian-safe pieces.

The module is side-effect free on import.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian", "crosses_antimeridian"]

_PERIOD = 360.0
_HALF = 180.0
# Longitude jumps larger than this between consecutive vertices are read as an
# antimeridian wrap rather than as a genuine east-west traverse.
_JUMP = 180.0


def _rings(polygon: Polygon) -> Iterable[Sequence[Tuple[float, float]]]:
    yield list(polygon.exterior.coords)
    for interior in polygon.interiors:
        yield list(interior.coords)


def crosses_antimeridian(polygon: Polygon) -> bool:
    """True if any ring has consecutive vertices that jump across +/-180."""
    if polygon.is_empty:
        return False
    for ring in _rings(polygon):
        for (lon_a, *_), (lon_b, *_) in zip(ring, ring[1:]):
            if abs(lon_b - lon_a) > _JUMP:
                return True
    return False


def _unwrap(ring: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Remove the +/-180 discontinuity from a ring's longitudes.

    Longitudes become continuous but may leave [-180, 180]; latitudes and any
    further ordinates are passed through untouched.
    """
    out: List[Tuple[float, float]] = []
    offset = 0.0
    prev_lon = None
    for vertex in ring:
        lon = vertex[0]
        if prev_lon is not None:
            delta = lon - prev_lon
            if abs(delta) > _JUMP:
                offset -= _PERIOD * round(delta / _PERIOD)
        prev_lon = lon
        out.append((lon + offset,) + tuple(vertex[1:]))
    return out


def _recentre(ring: List[Tuple[float, float]], target: float) -> List[Tuple[float, float]]:
    """Shift a ring by whole periods so it sits in the same lobe as `target`."""
    mid = 0.5 * (min(v[0] for v in ring) + max(v[0] for v in ring))
    shift = -_PERIOD * round((mid - target) / _PERIOD)
    if shift == 0.0:
        return ring
    return [(v[0] + shift,) + tuple(v[1:]) for v in ring]


def _shift(geom: BaseGeometry, dx: float) -> BaseGeometry:
    if dx == 0.0:
        return geom
    from shapely.affinity import translate

    return translate(geom, xoff=dx)


def _polygons(geom: BaseGeometry) -> List[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [p for p in geom.geoms if not p.is_empty]
    if hasattr(geom, "geoms"):
        out: List[Polygon] = []
        for part in geom.geoms:
            out.extend(_polygons(part))
        return out
    return []


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split `polygon` at the antimeridian.

    `polygon` is interpreted as EPSG:4326 lon/lat with longitudes in
    [-180, 180]. A polygon whose edges wrap across the antimeridian is cut into
    pieces, each of which lies wholly within one [-180, 180] lobe and touches
    the antimeridian only along its boundary. The returned pieces cover exactly
    the region the input covers. A polygon that does not wrap is returned as a
    single-element list, unchanged.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("split_antimeridian expects a shapely Polygon")
    if polygon.is_empty or not crosses_antimeridian(polygon):
        return [polygon]

    exterior = _unwrap(list(polygon.exterior.coords))
    centre = 0.5 * (min(v[0] for v in exterior) + max(v[0] for v in exterior))
    interiors = [
        _recentre(_unwrap(list(ring.coords)), centre) for ring in polygon.interiors
    ]

    unwrapped: BaseGeometry = Polygon(exterior, interiors)
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)

    min_lon, min_lat, max_lon, max_lat = unwrapped.bounds
    # Pad latitudes so the clipping strips fully contain the geometry.
    lat_lo, lat_hi = min_lat - 1.0, max_lat + 1.0

    first = int(math.floor((min_lon + _HALF) / _PERIOD))
    last = int(math.floor((max_lon + _HALF) / _PERIOD))

    pieces: List[Polygon] = []
    for k in range(first, last + 1):
        strip = box(-_HALF + k * _PERIOD, lat_lo, _HALF + k * _PERIOD, lat_hi)
        clipped = unwrapped.intersection(strip)
        for part in _polygons(clipped):
            moved = _shift(part, -_PERIOD * k)
            if not moved.is_valid:
                moved = make_valid(moved)
            pieces.extend(p for p in _polygons(moved) if p.area > 0.0)

    return pieces if pieces else [polygon]