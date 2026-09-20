"""Split polygons that cross the antimeridian into antimeridian-safe pieces.

The single public entry point is :func:`split_antimeridian`.
"""

from __future__ import annotations

import math
from typing import List, Sequence

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_HALF = 180.0


def _unwrap(xs: Sequence[float]) -> List[float]:
    """Remove +/-360 jumps from a sequence of longitudes.

    Consecutive vertices of a ring are assumed to be less than 180 degrees
    apart along the shorter path, which is what an antimeridian crossing
    encoded in [-180, 180] looks like.
    """
    out = [float(xs[0])]
    offset = 0.0
    for prev, cur in zip(xs, xs[1:]):
        delta = float(cur) - float(prev)
        if delta > _HALF:
            offset -= _PERIOD
        elif delta < -_HALF:
            offset += _PERIOD
        out.append(float(cur) + offset)
    return out


def _unwrap_ring(coords: Sequence[Sequence[float]]) -> List[tuple]:
    xs = _unwrap([c[0] for c in coords])
    return [(x, float(c[1])) for x, c in zip(xs, coords)]


def _align_to(ring: List[tuple], lo: float, hi: float) -> List[tuple]:
    """Shift a ring by a whole number of periods so it sits inside [lo, hi]."""
    ring_lo = min(x for x, _ in ring)
    ring_hi = max(x for x, _ in ring)
    if ring_lo >= lo and ring_hi <= hi:
        return ring
    # Move the ring's centre as close as possible to the shell's centre.
    shift = round(((lo + hi) / 2.0 - (ring_lo + ring_hi) / 2.0) / _PERIOD) * _PERIOD
    if shift == 0.0:
        return ring
    return [(x + shift, y) for x, y in ring]


def _collect_polygons(geom: BaseGeometry, out: List[Polygon]) -> None:
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        if geom.area > 0:
            out.append(geom)
    elif isinstance(geom, MultiPolygon):
        for part in geom.geoms:
            _collect_polygons(part, out)
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            _collect_polygons(part, out)


def _shift(polygon: Polygon, dx: float) -> Polygon:
    if dx == 0.0:
        return polygon
    shell = [(x + dx, y) for x, y in polygon.exterior.coords]
    holes = [[(x + dx, y) for x, y in ring.coords] for ring in polygon.interiors]
    return Polygon(shell, holes)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    ``polygon`` is a shapely :class:`~shapely.geometry.Polygon` in EPSG:4326
    with longitudes in [-180, 180].  If it crosses the antimeridian -- i.e.
    consecutive vertices jump between values near +180 and near -180 -- it is
    cut into several polygons whose union covers the same region and none of
    which spans the antimeridian.  A polygon that does not cross is returned
    unchanged as a single-element list.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("split_antimeridian expects a shapely Polygon")
    if polygon.is_empty:
        return [polygon]

    shell = _unwrap_ring(list(polygon.exterior.coords))
    shell_lo = min(x for x, _ in shell)
    shell_hi = max(x for x, _ in shell)

    holes = []
    for ring in polygon.interiors:
        holes.append(_align_to(_unwrap_ring(list(ring.coords)), shell_lo, shell_hi))

    lo = min([shell_lo] + [min(x for x, _ in h) for h in holes])
    hi = max([shell_hi] + [max(x for x, _ in h) for h in holes])

    # Nothing to do: the unwrapped polygon already fits in a single [-180, 180]
    # window at its original position.
    if shell_lo >= -_HALF and shell_hi <= _HALF:
        return [polygon]

    unwrapped = Polygon(shell, holes)
    if not unwrapped.is_valid:
        unwrapped = unwrapped.buffer(0)

    miny, maxy = polygon.bounds[1], polygon.bounds[3]
    pad = 1.0 if maxy - miny == 0 else 0.0
    ylo, yhi = miny - pad - 1.0, maxy + pad + 1.0

    first = int(math.floor((lo + _HALF) / _PERIOD))
    last = int(math.floor((hi + _HALF) / _PERIOD))
    if hi == (last * _PERIOD - _HALF):  # upper edge exactly on a strip boundary
        last -= 1

    pieces: List[Polygon] = []
    for k in range(first, last + 1):
        strip = box(k * _PERIOD - _HALF, ylo, k * _PERIOD + _HALF, yhi)
        clipped: List[Polygon] = []
        _collect_polygons(unwrapped.intersection(strip), clipped)
        for part in clipped:
            pieces.append(_shift(part, -k * _PERIOD))

    if not pieces:
        return [polygon]
    return pieces