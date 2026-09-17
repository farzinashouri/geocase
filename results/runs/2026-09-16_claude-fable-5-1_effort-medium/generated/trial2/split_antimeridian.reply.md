```python
"""Split a lon/lat (EPSG:4326) polygon that crosses the antimeridian.

The single public function is :func:`split_antimeridian`.  Importing this
module has no side effects.
"""
from __future__ import annotations

import math
from typing import List

import numpy as np
from shapely import affinity
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_HALF_TURN = 180.0
_FULL_TURN = 360.0
_EPS = 1e-9


def _ring_xy(ring) -> np.ndarray:
    """Return an (n, 2) float array of lon/lat for a shapely ring."""
    return np.asarray(ring.coords, dtype=float)[:, :2]


def _crosses(pts: np.ndarray) -> bool:
    """True when consecutive longitudes jump by more than 180 degrees."""
    return bool(np.any(np.abs(np.diff(pts[:, 0])) > _HALF_TURN))


def _unwrap(pts: np.ndarray) -> np.ndarray:
    """Make longitudes continuous by adding +-360 after each antimeridian jump."""
    lons = pts[:, 0]
    d = np.diff(lons)
    step = np.where(d > _HALF_TURN, -_FULL_TURN, np.where(d < -_HALF_TURN, _FULL_TURN, 0.0))
    shift = np.concatenate([[0.0], np.cumsum(step)])
    return np.column_stack([lons + shift, pts[:, 1]])


def _close(pts: np.ndarray) -> np.ndarray:
    """Close an unwrapped ring; a ring encircling a pole is closed via that pole."""
    gap = pts[-1, 0] - pts[0, 0]
    if abs(gap) < _EPS and abs(pts[-1, 1] - pts[0, 1]) < _EPS:
        return pts
    if abs(abs(gap) - _FULL_TURN) < 1e-6:
        pole = 90.0 if pts[:, 1].mean() >= 0.0 else -90.0
        extra = np.array(
            [[pts[-1, 0], pole], [pts[0, 0], pole], [pts[0, 0], pts[0, 1]]], dtype=float
        )
        return np.vstack([pts, extra])
    return np.vstack([pts, pts[:1]])


def _align(hole: np.ndarray, ext_center: float) -> np.ndarray:
    """Shift an unwrapped hole by a multiple of 360 so it sits inside the exterior."""
    hole_center = 0.5 * (hole[:, 0].min() + hole[:, 0].max())
    k = round((ext_center - hole_center) / _FULL_TURN)
    if k:
        hole = hole.copy()
        hole[:, 0] += k * _FULL_TURN
    return hole


def _polygons(geom: BaseGeometry) -> List[Polygon]:
    """Flatten any geometry into a list of non-empty Polygons."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        out: List[Polygon] = []
        for g in geom.geoms:
            out.extend(_polygons(g))
        return out
    return []


def _valid(poly: BaseGeometry) -> BaseGeometry:
    if poly.is_valid:
        return poly
    fixed = make_valid(poly)
    return fixed if fixed.is_valid else poly.buffer(0)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` (lon/lat, lon in [-180, 180]) at the antimeridian.

    Returns a list of valid polygons covering the same region, none of which
    crosses the antimeridian.  A polygon that does not cross it is returned
    unchanged as a one-element list.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("split_antimeridian expects a shapely Polygon")
    if polygon.is_empty:
        return [polygon]

    rings = [_ring_xy(polygon.exterior)] + [_ring_xy(r) for r in polygon.interiors]
    if not any(_crosses(r) for r in rings):
        return [polygon]

    exterior = _close(_unwrap(rings[0]))
    ext_min, ext_max = exterior[:, 0].min(), exterior[:, 0].max()
    ext_center = 0.5 * (ext_min + ext_max)
    holes = [_align(_close(_unwrap(h)), ext_center) for h in rings[1:]]

    unwrapped = _valid(Polygon(exterior, holes))
    minx, _, maxx, _ = unwrapped.bounds

    # Antimeridian images in unwrapped space: x = 180 + 360k strictly inside bounds.
    k_lo = math.ceil((minx - _HALF_TURN) / _FULL_TURN)
    k_hi = math.floor((maxx - _HALF_TURN) / _FULL_TURN)
    cuts = [_HALF_TURN + _FULL_TURN * k for k in range(k_lo, k_hi + 1)]
    cuts = [c for c in cuts if minx + _EPS < c < maxx - _EPS]
    edges = [minx] + cuts + [maxx]

    result: List[Polygon] = []
    for x0, x1 in zip(edges[:-1], edges[1:]):
        if x1 - x0 <= _EPS:
            continue
        piece = unwrapped.intersection(box(x0, -90.0, x1, 90.0))
        center = 0.5 * (x0 + x1)
        k = math.floor((center + _HALF_TURN) / _FULL_TURN)
        if k:
            piece = affinity.translate(piece, xoff=-k * _FULL_TURN)
        for p in _polygons(_valid(piece)):
            if p.area > 0.0:
                result.append(p)

    return result if result else [polygon]
```