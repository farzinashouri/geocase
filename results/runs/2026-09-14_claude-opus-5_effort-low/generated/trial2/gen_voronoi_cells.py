"""Rectangle-clipped Voronoi cells for a set of planar points.

Importing this module has no side effects.
"""

from __future__ import annotations

import shapely
from shapely.geometry import MultiPoint, Point, Polygon, box

__all__ = ["voronoi_cells"]


def voronoi_cells(points, bounds):
    """Return the Voronoi cell of each input point, clipped to ``bounds``.

    Parameters
    ----------
    points : list of (x, y)
        N distinct points in a projected (planar) coordinate system.
    bounds : (minx, miny, maxx, maxy)
        Rectangle containing all the points.

    Returns
    -------
    list of shapely.geometry.Polygon
        The i-th polygon is the set of locations inside the rectangle that are
        strictly closer to ``points[i]`` than to any other input point (closed
        up to its boundary, which is shared with the neighbouring cells).
    """
    pts = [(float(x), float(y)) for x, y in points]
    if not pts:
        return []

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if minx > maxx:
        minx, maxx = maxx, minx
    if miny > maxy:
        miny, maxy = maxy, miny
    rect = box(minx, miny, maxx, maxy)

    if len(pts) == 1:
        return [rect]

    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")

    # `extend_to` only guarantees the diagram reaches the given envelope, so pad
    # generously and clip afterwards; padding also keeps the ragged outer edges
    # of the raw diagram well away from the rectangle.
    span = max(maxx - minx, maxy - miny, 1.0)
    pad = 10.0 * span
    envelope = box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    raw = shapely.voronoi_polygons(MultiPoint(pts), extend_to=envelope)
    cells = [g for g in shapely.get_parts(raw) if not g.is_empty]

    # Associate each raw cell with the generating point it contains.
    tree = shapely.STRtree(cells)
    assigned = [None] * len(pts)
    for i, (x, y) in enumerate(pts):
        p = Point(x, y)
        candidates = tree.query(p)
        chosen = None
        for j in candidates:
            if cells[j].intersects(p):
                chosen = cells[j]
                break
        if chosen is None:
            # Numerically ambiguous placement (e.g. a point exactly on a shared
            # cell boundary): fall back to the nearest cell.
            chosen = cells[tree.nearest(p)]
        assigned[i] = chosen

    result = []
    for cell in assigned:
        clipped = cell.intersection(rect)
        if clipped.is_empty:
            clipped = Polygon()
        elif clipped.geom_type != "Polygon":
            # Degenerate slivers may yield lines/points alongside the area part;
            # keep the largest polygonal component.
            polys = [g for g in shapely.get_parts(clipped) if g.geom_type == "Polygon"]
            clipped = max(polys, key=lambda g: g.area) if polys else Polygon()
        result.append(clipped)

    return result