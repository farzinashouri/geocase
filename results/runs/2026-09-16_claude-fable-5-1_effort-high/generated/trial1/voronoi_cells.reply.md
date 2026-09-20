Here is the module.

```python
"""Bounded Voronoi cells for a set of distinct planar points.

`voronoi_cells(points, bounds)` returns, for every input point, the polygon
consisting of the locations inside `bounds` that are closer to that point than
to any other input point. Results are returned in input order.

The primary path uses GEOS's Voronoi builder through shapely and clips each
cell to the rectangle. A pure-Python half-plane clipping fallback guarantees a
correct answer for tiny inputs and for any case where the GEOS result cannot
be matched one-to-one with the input sites.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

Point2D = Tuple[float, float]
Bounds = Tuple[float, float, float, float]

__all__ = ["voronoi_cells"]


def voronoi_cells(points: Sequence[Point2D], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of each point, clipped to `bounds`.

    Parameters
    ----------
    points:
        Sequence of N distinct ``(x, y)`` tuples in a planar coordinate system.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle containing all the points.

    Returns
    -------
    list of shapely.geometry.Polygon
        The i-th polygon is the part of the rectangle closer to ``points[i]``
        than to any other input point.
    """
    pts: List[Point2D] = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be a non-degenerate rectangle")
    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")
    for x, y in pts:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x}, {y}) lies outside bounds")

    n = len(pts)
    rect = box(minx, miny, maxx, maxy)
    if n == 0:
        return []
    if n == 1:
        return [rect]

    cells = _cells_via_geos(pts, rect) if n >= 3 else None
    if cells is None:
        cells = [_cell_via_halfplanes(i, pts, rect) for i in range(n)]
    return cells


# --------------------------------------------------------------------------- #
# Primary path: GEOS Voronoi diagram, matched back to the input order.
# --------------------------------------------------------------------------- #
def _cells_via_geos(pts: List[Point2D], rect: Polygon) -> Optional[List[Polygon]]:
    n = len(pts)
    arr = np.asarray(pts, dtype=float)
    try:
        sites = shapely.points(arr)
        diagram = shapely.voronoi_polygons(
            shapely.multipoints(arr), tolerance=0.0, extend_to=rect
        )
    except Exception:  # pragma: no cover - defensive; fallback handles it
        return None

    raw = [g for g in shapely.get_parts(diagram) if isinstance(g, Polygon)]
    if len(raw) != n:
        return None

    # Each site lies strictly inside its own (unclipped) cell, so a `within`
    # query gives an unambiguous one-to-one match between sites and cells.
    tree = STRtree(raw)
    site_idx, cell_idx = tree.query(sites, predicate="within")
    if (
        len(site_idx) != n
        or len(set(site_idx.tolist())) != n
        or len(set(cell_idx.tolist())) != n
    ):
        return None

    ordered: List[Optional[Polygon]] = [None] * n
    for s, c in zip(site_idx.tolist(), cell_idx.tolist()):
        ordered[s] = raw[c]

    out: List[Polygon] = []
    for cell in ordered:
        clipped = _largest_polygon(cell.intersection(rect))
        if clipped is None or clipped.is_empty or not clipped.is_valid:
            return None
        out.append(clipped)

    # Sanity check: the cells must tile the rectangle.
    total = sum(p.area for p in out)
    if not math.isclose(total, rect.area, rel_tol=1e-7, abs_tol=1e-9 * rect.area):
        return None
    return out


def _largest_polygon(geom) -> Optional[Polygon]:
    """Extract the single polygonal part of a (possibly mixed) geometry."""
    if isinstance(geom, Polygon):
        return geom
    best: Optional[Polygon] = None
    for part in shapely.get_parts(geom):
        if isinstance(part, Polygon) and (best is None or part.area > best.area):
            best = part
    return best


# --------------------------------------------------------------------------- #
# Fallback path: intersect the rectangle with N-1 half-planes per site.
# --------------------------------------------------------------------------- #
def _cell_via_halfplanes(i: int, pts: List[Point2D], rect: Polygon) -> Polygon:
    xi, yi = pts[i]
    coords: List[Point2D] = list(rect.exterior.coords)[:-1]
    for j, (xj, yj) in enumerate(pts):
        if j == i:
            continue
        # |p - pi|^2 <= |p - pj|^2  <=>  2(pj - pi) . p <= |pj|^2 - |pi|^2
        a = 2.0 * (xj - xi)
        b = 2.0 * (yj - yi)
        c = (xj * xj + yj * yj) - (xi * xi + yi * yi)
        coords = _clip_halfplane(coords, a, b, c)
        if len(coords) < 3:
            break
    if len(coords) < 3:
        # Cannot happen for distinct sites inside the rectangle, but never
        # return an invalid geometry.
        return Polygon()
    return Polygon(coords)


def _clip_halfplane(
    coords: List[Point2D], a: float, b: float, c: float
) -> List[Point2D]:
    """Sutherland-Hodgman clip of a convex polygon against a*x + b*y <= c."""
    out: List[Point2D] = []
    m = len(coords)
    for k in range(m):
        p = coords[k - 1]
        q = coords[k]
        fp = a * p[0] + b * p[1] - c
        fq = a * q[0] + b * q[1] - c
        p_in = fp <= 0.0
        q_in = fq <= 0.0
        if q_in:
            if not p_in:
                out.append(_intersect(p, q, fp, fq))
            out.append(q)
        elif p_in:
            out.append(_intersect(p, q, fp, fq))
    return out


def _intersect(p: Point2D, q: Point2D, fp: float, fq: float) -> Point2D:
    t = fp / (fp - fq)
    return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
```