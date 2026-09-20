"""Bounded Voronoi cells for planar points.

Provides :func:`voronoi_cells`, which returns, for each input point, the
portion of a rectangle that is closer to that point than to any other input
point. Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from shapely.geometry import (
    GeometryCollection,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.ops import voronoi_diagram, unary_union
from shapely.strtree import STRtree

Coord = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def _as_polygon(geom) -> Polygon:
    """Reduce an intersection result to a single Polygon (largest by area)."""
    if geom.is_empty:
        return Polygon()
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        polys = [g for g in geom.geoms if isinstance(g, Polygon) and not g.is_empty]
        if not polys:
            return Polygon()
        if len(polys) == 1:
            return polys[0]
        merged = unary_union(polys)
        if isinstance(merged, Polygon):
            return merged
        return max(merged.geoms, key=lambda p: p.area)
    return Polygon()


def _half_plane(pi: Coord, pj: Coord, radius: float) -> Polygon:
    """Large polygon approximating the half-plane of points closer to pi than pj."""
    mx, my = (pi[0] + pj[0]) / 2.0, (pi[1] + pj[1]) / 2.0
    dx, dy = pj[0] - pi[0], pj[1] - pi[1]
    norm = math.hypot(dx, dy)
    ux, uy = dx / norm, dy / norm          # unit vector from pi toward pj
    tx, ty = -uy, ux                       # unit vector along the bisector
    # Rectangle: along the bisector +/- radius, and from the bisector back
    # toward pi (opposite of u) by 2*radius.
    a = (mx + tx * radius, my + ty * radius)
    b = (mx - tx * radius, my - ty * radius)
    c = (b[0] - ux * 2 * radius, b[1] - uy * 2 * radius)
    d = (a[0] - ux * 2 * radius, a[1] - uy * 2 * radius)
    return Polygon([a, b, c, d])


def _cells_by_half_planes(points: Sequence[Coord], rect: Polygon) -> List[Polygon]:
    """Exact O(N^2) fallback: clip the rectangle by every bisector half-plane."""
    minx, miny, maxx, maxy = rect.bounds
    radius = 4.0 * math.hypot(maxx - minx, maxy - miny) + 1.0
    out: List[Polygon] = []
    for i, pi in enumerate(points):
        cell = rect
        for j, pj in enumerate(points):
            if i == j:
                continue
            cell = _as_polygon(cell.intersection(_half_plane(pi, pj, radius)))
            if cell.is_empty:
                break
        out.append(cell)
    return out


def voronoi_cells(points: Sequence[Coord], bounds: Bounds) -> List[Polygon]:
    """Return the bounded Voronoi cell of each point, in input order.

    Parameters
    ----------
    points : list of (x, y)
        N distinct planar coordinates, all inside ``bounds``.
    bounds : (minx, miny, maxx, maxy)
        Clipping rectangle.

    Returns
    -------
    list of shapely.geometry.Polygon
        ``result[i]`` is the part of the rectangle closer to ``points[i]``
        than to any other input point.
    """
    pts = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    rect = box(minx, miny, maxx, maxy)
    n = len(pts)

    if n == 0:
        return []
    if n == 1:
        return [rect]
    if len(set(pts)) != n:
        raise ValueError("points must be distinct")

    # Fast path: GEOS Voronoi diagram, extended to cover the bounds, then
    # matched back to the input points and clipped to the rectangle.
    try:
        pad = max(maxx - minx, maxy - miny, 1.0)
        envelope = box(minx - pad, miny - pad, maxx + pad, maxy + pad)
        diagram = voronoi_diagram(MultiPoint(pts), envelope=envelope)
        cells = [g for g in diagram.geoms if isinstance(g, Polygon)]
        if len(cells) != n:
            raise RuntimeError("unexpected cell count")

        tree = STRtree(cells)
        result: List[Polygon] = [None] * n  # type: ignore[list-item]
        used = set()
        for i, p in enumerate(pts):
            pt = Point(p)
            hits = [k for k in tree.query(pt, predicate="intersects") if k not in used]
            if not hits:
                raise RuntimeError("site not covered by a cell")
            if len(hits) > 1:
                # Degenerate boundary contact; pick the cell containing the
                # site interior, else the nearest by distance to the site.
                hits.sort(key=lambda k: (not cells[k].contains(pt), cells[k].distance(pt)))
            k = int(hits[0])
            used.add(k)
            result[i] = _as_polygon(cells[k].intersection(rect))
        if any(r is None or r.is_empty for r in result):
            raise RuntimeError("empty cell after clipping")
        return result
    except Exception:
        # Robust fallback for degenerate configurations (e.g. collinear sites).
        return _cells_by_half_planes(pts, rect)