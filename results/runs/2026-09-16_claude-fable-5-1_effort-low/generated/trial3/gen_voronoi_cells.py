"""Bounded Voronoi cells for a set of planar points.

Each cell is the intersection of the bounding rectangle with the half-planes
"closer to p_i than to p_j" for every other point p_j. This is exact (up to
floating point) and handles collinear/degenerate configurations that trip up
Delaunay-based approaches.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from shapely.geometry import Polygon, box

Point = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def _half_plane(p: Point, q: Point, bounds: Bounds) -> Polygon:
    """Polygon covering the part of `bounds` closer to p than to q.

    Built as a large rectangle in the frame of the bisector, then clipped to
    the bounds. The rectangle is sized so it always fully covers the bounds.
    """
    minx, miny, maxx, maxy = bounds
    px, py = p
    qx, qy = q
    # Midpoint of p-q and unit direction from q toward p.
    mx, my = (px + qx) / 2.0, (py + qy) / 2.0
    dx, dy = px - qx, py - qy
    d = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / d, dy / d  # normal pointing to p's side
    tx, ty = -uy, ux  # tangent along the bisector

    # Radius large enough to enclose the bounds from the midpoint.
    span = max(maxx - minx, maxy - miny)
    r = 2.0 * (span + max(abs(mx - minx), abs(mx - maxx), abs(my - miny), abs(my - maxy))) + 1.0

    corners = [
        (mx + tx * r, my + ty * r),
        (mx + tx * r + ux * r, my + ty * r + uy * r),
        (mx - tx * r + ux * r, my - ty * r + uy * r),
        (mx - tx * r, my - ty * r),
    ]
    return Polygon(corners)


def voronoi_cells(points: Sequence[Point], bounds: Bounds) -> list[Polygon]:
    """Return the Voronoi cell of each point clipped to `bounds`.

    Args:
        points: list of N distinct (x, y) tuples in a planar coordinate system.
        bounds: (minx, miny, maxx, maxy) rectangle containing all the points.

    Returns:
        List of N shapely Polygons; the i-th polygon is the set of locations
        within `bounds` closer to points[i] than to any other point.
    """
    pts = [(float(x), float(y)) for x, y in points]
    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be a non-degenerate rectangle")

    rect = box(minx, miny, maxx, maxy)
    b = (minx, miny, maxx, maxy)
    cells: list[Polygon] = []
    for i, p in enumerate(pts):
        cell = rect
        for j, q in enumerate(pts):
            if i == j:
                continue
            cell = cell.intersection(_half_plane(p, q, b))
            if cell.is_empty:
                break
        if cell.geom_type != "Polygon":
            # Intersection of convex sets is convex, so at most one polygon;
            # take the polygonal part if a collection sneaks through.
            polys = [g for g in getattr(cell, "geoms", []) if g.geom_type == "Polygon"]
            cell = polys[0] if polys else Polygon()
        cells.append(cell)
    return cells