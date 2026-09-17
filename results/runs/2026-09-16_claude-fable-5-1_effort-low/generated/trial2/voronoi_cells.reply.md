```python
"""Bounded Voronoi cells on a plane using shapely."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from shapely.geometry import Point, Polygon, box
from shapely.ops import voronoi_diagram
from shapely.strtree import STRtree


def voronoi_cells(
    points: Sequence[Tuple[float, float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    """Return the Voronoi cell of each input point clipped to ``bounds``.

    ``points`` are distinct (x, y) tuples in a planar coordinate system.
    ``bounds`` is (minx, miny, maxx, maxy) and must contain all points.
    The i-th returned polygon is the set of locations in the rectangle
    that are closer to points[i] than to any other input point.
    """
    pts = [tuple(map(float, p)) for p in points]
    n = len(pts)
    minx, miny, maxx, maxy = map(float, bounds)
    rect = box(minx, miny, maxx, maxy)

    if n == 0:
        return []
    if n == 1:
        return [rect]

    # Envelope large enough that every clipped cell is correct: shapely's
    # voronoi_diagram extends unbounded cells to the given envelope, and
    # they must reach past the rectangle we clip with.
    pad = max(maxx - minx, maxy - miny) * 2.0 + 1.0
    envelope = box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    multipoint = Point(pts[0]).union(Point(pts[1]))
    for p in pts[2:]:
        multipoint = multipoint.union(Point(p))
    # Faster/cleaner MultiPoint construction:
    from shapely.geometry import MultiPoint

    multipoint = MultiPoint(pts)

    diagram = voronoi_diagram(multipoint, envelope=envelope, tolerance=0.0)
    cells = list(diagram.geoms)

    # voronoi_diagram does not guarantee output order; match each cell to
    # the input point it contains.
    tree = STRtree(cells)
    out: List[Polygon] = [None] * n  # type: ignore[list-item]
    for i, p in enumerate(pts):
        pt = Point(p)
        candidates = tree.query(pt)
        chosen = None
        for idx in candidates:
            if cells[idx].covers(pt):
                chosen = cells[idx]
                break
        if chosen is None:
            # Numerical edge case: fall back to nearest cell.
            chosen = cells[tree.nearest(pt)]
        clipped = chosen.intersection(rect)
        if clipped.geom_type != "Polygon":
            # Keep the largest polygonal piece if intersection produced a
            # collection (should not happen for convex cells and a box).
            polys = [g for g in getattr(clipped, "geoms", []) if g.geom_type == "Polygon"]
            clipped = max(polys, key=lambda g: g.area) if polys else Polygon()
        out[i] = clipped
    return out
```