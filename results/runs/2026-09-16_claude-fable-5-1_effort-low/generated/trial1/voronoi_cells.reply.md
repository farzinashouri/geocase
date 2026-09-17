```python
"""Bounded Voronoi cells for a set of planar points.

voronoi_cells(points, bounds) returns, for each input point, the shapely
Polygon consisting of the locations inside the bounding rectangle that are
closer to that point than to any other input point.

The construction is the direct half-plane intersection definition: each cell
is the rectangle clipped by the perpendicular-bisector half-planes toward
every other point. This is O(N^2) but exact (up to floating point) and has
no dependency on scipy or on unbounded-region handling.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from shapely.geometry import Polygon, box

Point = Tuple[float, float]


def _half_plane(p: Point, q: Point, bounds: Sequence[float]) -> Polygon:
    """Polygon covering the part of the plane closer to p than to q.

    Built as a large rectangle (comfortably containing `bounds`) split along
    the perpendicular bisector of pq; the side containing p is returned.
    """
    px, py = p
    qx, qy = q
    minx, miny, maxx, maxy = bounds

    # Midpoint of pq and direction of the bisector line.
    mx, my = (px + qx) / 2.0, (py + qy) / 2.0
    dx, dy = qx - px, qy - py
    # Bisector direction is perpendicular to (dx, dy).
    ux, uy = -dy, dx
    norm = math.hypot(ux, uy)
    ux, uy = ux / norm, uy / norm
    # Inward normal pointing toward p.
    nx, ny = -dx / norm, -dy / norm

    # Extent large enough that the half-plane polygon fully covers `bounds`.
    span = math.hypot(maxx - minx, maxy - miny) + math.hypot(
        mx - (minx + maxx) / 2.0, my - (miny + maxy) / 2.0
    )
    r = 4.0 * span + 1.0

    a = (mx + ux * r, my + uy * r)
    b = (mx - ux * r, my - uy * r)
    c = (b[0] + nx * r, b[1] + ny * r)
    d = (a[0] + nx * r, a[1] + ny * r)
    return Polygon([a, b, c, d])


def voronoi_cells(points: Iterable[Point], bounds: Sequence[float]) -> List[Polygon]:
    """Return the bounded Voronoi cell of each point, in input order.

    Args:
        points: list of N distinct (x, y) tuples in a planar CRS.
        bounds: (minx, miny, maxx, maxy) rectangle containing all points.

    Returns:
        List of N shapely Polygons; the i-th polygon is the set of locations
        in the rectangle closer to points[i] than to any other point.
    """
    pts = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if minx >= maxx or miny >= maxy:
        raise ValueError("bounds must be a non-degenerate rectangle")
    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")

    rect = box(minx, miny, maxx, maxy)
    if not pts:
        return []
    if len(pts) == 1:
        return [rect]

    cells: List[Polygon] = []
    for i, p in enumerate(pts):
        cell = rect
        for j, q in enumerate(pts):
            if i == j:
                continue
            cell = cell.intersection(_half_plane(p, q, (minx, miny, maxx, maxy)))
            if cell.is_empty:
                break
        if cell.geom_type != "Polygon":
            # Intersections of convex sets are convex, so this only happens
            # on numerical collapse; keep the largest polygonal piece.
            parts = [g for g in getattr(cell, "geoms", []) if g.geom_type == "Polygon"]
            cell = max(parts, key=lambda g: g.area) if parts else Polygon()
        cells.append(cell)
    return cells
```