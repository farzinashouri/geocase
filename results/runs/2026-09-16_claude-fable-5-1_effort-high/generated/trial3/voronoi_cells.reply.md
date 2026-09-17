The scratch-file write was declined, so I'm delivering the module without running a local check. It uses GEOS's Voronoi builder as the fast path and validates the result, falling back to a direct half-plane construction if validation fails.

```python
"""Bounded Voronoi cells for planar points.

``voronoi_cells(points, bounds)`` returns one shapely ``Polygon`` per input
point, in input order.  The i-th polygon is the part of the bounding rectangle
whose locations are nearer to the i-th point than to any other point.

Fast path: GEOS's Voronoi builder via ``shapely.voronoi_polygons``, with the
resulting cells clipped to the rectangle and re-ordered to match the inputs.
Fallback (used only if the fast path cannot be validated): each cell is built
directly as the intersection of the rectangle with the half-planes
``{x : |x - p_i| <= |x - p_j|}``, which is the definition of a Voronoi cell and
depends on nothing but robust convex-polygon clipping.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import MultiPoint, Polygon, box

Coord = Tuple[float, float]
Bounds = Tuple[float, float, float, float]

__all__ = ["voronoi_cells"]


def voronoi_cells(points: Sequence[Coord], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of each point, clipped to ``bounds``.

    Parameters
    ----------
    points:
        Distinct ``(x, y)`` tuples in a planar coordinate system.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle containing all the points.

    Returns
    -------
    list of shapely.geometry.Polygon
        ``result[i]`` is the set of locations inside the rectangle that are
        closer to ``points[i]`` than to any other input point.
    """
    pts: List[Coord] = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be a non-degenerate rectangle")
    for x, y in pts:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x}, {y}) lies outside bounds {bounds}")
    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")

    rect = box(minx, miny, maxx, maxy)
    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        return [rect]

    cells = _cells_from_geos(pts, rect)
    if cells is None:
        cells = [_cell_from_halfplanes(i, pts, rect) for i in range(n)]
    return cells


# --------------------------------------------------------------------------- #
# Fast path: GEOS Voronoi diagram, clipped and re-ordered.
# --------------------------------------------------------------------------- #
def _cells_from_geos(pts: List[Coord], rect: Polygon) -> Optional[List[Polygon]]:
    """Cells in input order, or ``None`` if the result cannot be validated."""
    try:
        diagram = shapely.voronoi_polygons(MultiPoint(pts), extend_to=rect)
    except Exception:  # GEOS failure on degenerate input -> use fallback
        return None

    raw = [g for g in getattr(diagram, "geoms", [diagram]) if g.geom_type == "Polygon"]
    if len(raw) != len(pts):
        return None

    tree = STRtree(raw)
    site_geoms = shapely.points(np.asarray(pts, dtype=float))
    cells: List[Polygon] = []
    for site in site_geoms:
        hits = tree.query(site, predicate="within")
        if len(hits) != 1:
            return None
        cell = _as_single_polygon(raw[int(hits[0])].intersection(rect))
        if cell is None:
            return None
        cells.append(cell)

    # The cells must tile the rectangle exactly (up to floating-point noise).
    total = sum(c.area for c in cells)
    if not math.isclose(total, rect.area, rel_tol=1e-9, abs_tol=1e-12 * rect.area):
        return None
    return cells


# --------------------------------------------------------------------------- #
# Fallback: half-plane intersection straight from the definition.
# --------------------------------------------------------------------------- #
def _cell_from_halfplanes(i: int, pts: List[Coord], rect: Polygon) -> Polygon:
    px, py = pts[i]
    cell: Polygon = rect
    rminx, rminy, rmaxx, rmaxy = rect.bounds
    diag = math.hypot(rmaxx - rminx, rmaxy - rminy)

    others = sorted(
        (j for j in range(len(pts)) if j != i),
        key=lambda j: (pts[j][0] - px) ** 2 + (pts[j][1] - py) ** 2,
    )
    for j in others:
        qx, qy = pts[j]
        dist = math.hypot(qx - px, qy - py)
        # A bisector further away than every current vertex cannot cut the
        # cell, and neither can any later (more distant) bisector.
        reach = max(math.hypot(x - px, y - py) for x, y in cell.exterior.coords)
        if dist / 2.0 > reach:
            break
        half = _halfplane_toward(px, py, qx, qy, radius=2.0 * (diag + dist) + 1.0)
        clipped = _as_single_polygon(cell.intersection(half))
        if clipped is None:
            break
        cell = clipped
    return cell


def _halfplane_toward(px: float, py: float, qx: float, qy: float, radius: float) -> Polygon:
    """Large convex polygon covering ``{x : |x-p| <= |x-q|}`` within ``radius`` of the midpoint."""
    mx, my = (px + qx) / 2.0, (py + qy) / 2.0
    dist = math.hypot(qx - px, qy - py)
    ux, uy = (qx - px) / dist, (qy - py) / dist  # unit vector p -> q
    tx, ty = -uy, ux  # unit vector along the bisector
    r = radius
    return Polygon(
        [
            (mx + tx * r, my + ty * r),
            (mx + tx * r - ux * r, my + ty * r - uy * r),
            (mx - tx * r - ux * r, my - ty * r - uy * r),
            (mx - tx * r, my - ty * r),
        ]
    )


def _as_single_polygon(geom) -> Optional[Polygon]:
    """Reduce an overlay result to its single non-empty Polygon, or ``None``."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and not g.is_empty]
    if len(parts) == 1:
        return parts[0]
    return None
```