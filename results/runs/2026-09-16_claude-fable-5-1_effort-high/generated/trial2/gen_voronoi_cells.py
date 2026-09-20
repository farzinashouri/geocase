"""Bounded Voronoi cells on a planar coordinate system.

voronoi_cells(points, bounds) returns, for each input point, the shapely
Polygon consisting of every location inside `bounds` that is closer to that
point than to any other input point.

Only the standard library and shapely are required.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.strtree import STRtree

Coord = Tuple[float, float]
Bounds = Tuple[float, float, float, float]

__all__ = ["voronoi_cells"]


def _as_single_polygon(geom) -> Polygon | None:
    """Reduce an intersection result to a single Polygon (or None if empty)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        # A Voronoi cell and a rectangle are both convex, so their
        # intersection is a single convex polygon; anything else is a
        # numerical sliver, keep the dominant part.
        return max(geom.geoms, key=lambda p: p.area)
    if geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            return None
        return _as_single_polygon(shapely.union_all(polys))
    return None


def _half_plane_cells(pts: Sequence[Coord], clip: Polygon) -> List[Polygon]:
    """Exact O(N^2) construction: each cell is the box cut by N-1 half-planes.

    Used for tiny or degenerate inputs (e.g. all points collinear) where the
    Delaunay-based builder cannot be matched one-to-one to the inputs.
    """
    minx, miny, maxx, maxy = clip.bounds
    diag = math.hypot(maxx - minx, maxy - miny)
    reach = 2.0 * diag + 1.0  # comfortably covers the whole box from any midpoint

    cells: List[Polygon] = []
    for i, (xi, yi) in enumerate(pts):
        cell = clip
        for j, (xj, yj) in enumerate(pts):
            if i == j or cell.is_empty:
                continue
            dx, dy = xj - xi, yj - yi
            dist = math.hypot(dx, dy)
            if dist == 0.0:
                continue  # duplicate point; spec says points are distinct
            ux, uy = dx / dist, dy / dist          # unit vector i -> j
            px, py = -uy, ux                       # perpendicular
            mx, my = (xi + xj) / 2.0, (yi + yj) / 2.0  # bisector midpoint
            # Rectangle on the i-side of the perpendicular bisector.
            half_plane = Polygon(
                [
                    (mx + reach * px, my + reach * py),
                    (mx - reach * px, my - reach * py),
                    (mx - reach * px - reach * ux, my - reach * py - reach * uy),
                    (mx + reach * px - reach * ux, my + reach * py - reach * uy),
                ]
            )
            cell = _as_single_polygon(cell.intersection(half_plane)) or Polygon()
        cells.append(cell if cell.geom_type == "Polygon" else Polygon())
    return cells


def _geos_cells(pts: Sequence[Coord], clip: Polygon) -> List[Polygon] | None:
    """Fast path via GEOS. Returns None if cells cannot be matched to points."""
    try:
        raw = shapely.voronoi_polygons(MultiPoint(pts), extend_to=clip)
    except Exception:  # GEOS may reject degenerate configurations
        return None

    cells: List[Polygon] = []
    for part in shapely.get_parts(raw):
        poly = _as_single_polygon(part.intersection(clip))
        if poly is not None and poly.area > 0.0:
            cells.append(poly)

    if len(cells) != len(pts):
        return None

    tree = STRtree(cells)
    out: List[Polygon] = []
    used = set()
    for x, y in pts:
        p = Point(x, y)
        hits = list(tree.query(p, predicate="intersects"))
        if len(hits) != 1:
            # A site lies strictly inside its own cell, so any ambiguity
            # means numerical trouble; let the exact path handle it.
            return None
        idx = int(hits[0])
        if idx in used:
            return None
        used.add(idx)
        out.append(cells[idx])
    return out


def voronoi_cells(points: Iterable[Coord], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of each point, clipped to `bounds`.

    Parameters
    ----------
    points : iterable of (x, y)
        N distinct planar coordinates, all inside `bounds`.
    bounds : (minx, miny, maxx, maxy)
        Clipping rectangle.

    Returns
    -------
    list of shapely.Polygon
        The i-th polygon is the set of locations in the rectangle closer to
        points[i] than to any other input point. Cells tile the rectangle
        exactly (up to floating-point precision).
    """
    pts: List[Coord] = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    clip = box(minx, miny, maxx, maxy)

    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        return [Polygon(clip.exterior.coords)]

    if n >= 4:
        cells = _geos_cells(pts, clip)
        if cells is not None:
            return cells

    return _half_plane_cells(pts, clip)