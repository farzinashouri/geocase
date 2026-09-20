```python
"""Bounded Voronoi cells for a set of planar points.

voronoi_cells(points, bounds) returns, for each input point, the part of the
bounding rectangle that is closer to that point than to any other point.

The fast path uses shapely's GEOS-backed Voronoi diagram, verified against the
input; if verification fails (degenerate input such as collinear points, or any
GEOS error) the function falls back to an exact half-plane clipping construction
that works for every configuration of distinct points.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from shapely import STRtree
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import voronoi_diagram

Coord = Tuple[float, float]


def _clip_halfplane(vertices: List[Coord], p: Coord, q: Coord) -> List[Coord]:
    """Sutherland–Hodgman clip of a convex polygon to the half-plane closer to p than q."""
    px, py = p
    qx, qy = q
    # f(x, y) >= 0  <=>  (x, y) is at least as close to p as to q.
    ax, ay = qx - px, qy - py
    c = 0.5 * (qx * qx + qy * qy - px * px - py * py)

    def f(v: Coord) -> float:
        return c - (ax * v[0] + ay * v[1])

    out: List[Coord] = []
    n = len(vertices)
    for i in range(n):
        cur = vertices[i]
        prev = vertices[i - 1]
        fc, fp = f(cur), f(prev)
        if fc >= 0.0:
            if fp < 0.0:
                t = fp / (fp - fc)
                out.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
            out.append(cur)
        elif fp >= 0.0:
            t = fp / (fp - fc)
            out.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
    return out


def _halfplane_cells(points: Sequence[Coord], bounds: Tuple[float, float, float, float]) -> List[Polygon]:
    minx, miny, maxx, maxy = bounds
    rect = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)]
    cells: List[Polygon] = []
    for i, p in enumerate(points):
        verts = rect
        for j, q in enumerate(points):
            if i == j or not verts:
                continue
            verts = _clip_halfplane(verts, p, q)
        cells.append(Polygon(verts) if len(verts) >= 3 else Polygon())
    return cells


def _geos_cells(points: Sequence[Coord], bounds: Tuple[float, float, float, float]) -> List[Polygon]:
    minx, miny, maxx, maxy = bounds
    clip = box(minx, miny, maxx, maxy)
    # Envelope well beyond the bounds so every cell that touches the rectangle
    # is fully represented before clipping.
    margin = max(maxx - minx, maxy - miny, 1.0) * 10.0
    envelope = box(minx - margin, miny - margin, maxx + margin, maxy + margin)

    diagram = voronoi_diagram(MultiPoint(list(points)), envelope=envelope)
    raw = [g for g in diagram.geoms if not g.is_empty]
    tree = STRtree(raw)

    cells: List[Polygon] = []
    for p in points:
        hits = tree.query(Point(p), predicate="intersects")
        if len(hits) == 0:
            raise ValueError("no cell contains point")
        # A point on the shared edge of two cells would be a duplicate site,
        # which the contract excludes; take the cell that covers the site.
        cell = None
        for idx in hits:
            if raw[idx].covers(Point(p)):
                cell = raw[idx]
                break
        if cell is None:
            raise ValueError("no cell covers point")
        clipped = cell.intersection(clip)
        if clipped.geom_type == "MultiPolygon":
            clipped = max(clipped.geoms, key=lambda g: g.area)
        if clipped.geom_type != "Polygon":
            raise ValueError("unexpected clipped geometry")
        cells.append(clipped)

    # Verification: the cells must tile the rectangle without overlap.
    total = sum(c.area for c in cells)
    if abs(total - clip.area) > 1e-9 * max(clip.area, 1.0):
        raise ValueError("cells do not tile the bounds")
    if len(set(id(raw[tree.query(Point(p), predicate="within")[0]]) for p in points
               if len(tree.query(Point(p), predicate="within")) > 0)) != len(points):
        raise ValueError("cells not uniquely assigned")
    return cells


def voronoi_cells(points: Sequence[Coord], bounds: Tuple[float, float, float, float]) -> List[Polygon]:
    """Return one shapely Polygon per point: its Voronoi cell clipped to bounds.

    points: sequence of N distinct (x, y) tuples in a planar coordinate system.
    bounds: (minx, miny, maxx, maxy) rectangle containing all the points.
    The i-th polygon is the set of locations in the rectangle closer to
    points[i] than to any other input point.
    """
    pts = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if minx > maxx or miny > maxy:
        raise ValueError("bounds must be (minx, miny, maxx, maxy) with min <= max")
    if len(pts) == 0:
        return []
    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")
    if len(pts) == 1:
        return [box(minx, miny, maxx, maxy)]

    try:
        return _geos_cells(pts, (minx, miny, maxx, maxy))
    except Exception:
        return _halfplane_cells(pts, (minx, miny, maxx, maxy))
```