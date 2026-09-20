"""Bounded Voronoi cells.

``voronoi_cells(points, bounds)`` returns one shapely ``Polygon`` per input
point: the part of the bounding rectangle that lies closer to that point than
to any other input point (its Voronoi cell clipped to the rectangle).

Primary path: GEOS's Voronoi builder via ``shapely.voronoi_polygons``, clipped
to the rectangle and matched back to the generating points.  Fallback path
(only if GEOS returns something unexpected, e.g. for degenerate inputs):
direct half-plane clipping of the rectangle, one point at a time.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon, box

Bounds = Tuple[float, float, float, float]


def voronoi_cells(points: Sequence[Tuple[float, float]], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of each point, clipped to ``bounds``.

    Args:
        points: N distinct ``(x, y)`` tuples in a planar coordinate system.
        bounds: ``(minx, miny, maxx, maxy)`` rectangle containing every point.

    Returns:
        A list of N polygons; the i-th polygon is the set of locations inside
        the rectangle that are nearer to ``points[i]`` than to any other point.
    """
    pts = np.asarray(points, dtype=float)
    if pts.size == 0:
        return []
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")
    if not np.all(np.isfinite(pts)):
        raise ValueError("points must have finite coordinates")

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be (minx, miny, maxx, maxy) with positive extent")
    if not np.all((pts >= (minx, miny)) & (pts <= (maxx, maxy))):
        raise ValueError("every point must lie inside bounds")

    n = len(pts)
    if len(np.unique(pts, axis=0)) != n:
        raise ValueError("points must be distinct")

    rect = box(minx, miny, maxx, maxy)
    if n == 1:
        return [rect]

    cells = _cells_from_geos(pts, rect)
    if cells is None:
        cells = _cells_by_clipping(pts, rect)
    return cells


# --------------------------------------------------------------------------- #
# Primary path: GEOS Voronoi diagram
# --------------------------------------------------------------------------- #

def _cells_from_geos(pts: np.ndarray, rect: Polygon):
    """Build cells with GEOS; return None if the result is not a clean bijection."""
    n = len(pts)
    try:
        # GEOS clips the diagram to an envelope at least as large as ``rect``,
        # so intersecting with ``rect`` afterwards yields the exact bounded cell.
        diagram = shapely.voronoi_polygons(shapely.multipoints(pts), extend_to=rect)
    except Exception:
        return None

    raw = [g for g in shapely.get_parts(diagram) if not g.is_empty]
    if len(raw) != n:
        return None

    cells = [_single_polygon(g) for g in shapely.intersection(raw, rect)]
    if any(c is None for c in cells):
        return None

    # Every interior point of a Voronoi cell is strictly nearer to the cell's
    # generator than to any other site, so an interior point identifies the
    # generator unambiguously.
    inner = shapely.point_on_surface(cells)
    owner = shapely.STRtree(shapely.points(pts)).nearest(inner)
    owner = np.asarray(owner, dtype=int).reshape(-1)
    if owner.size != n or np.unique(owner).size != n:
        return None

    ordered: List[Polygon] = [None] * n  # type: ignore[list-item]
    for cell, i in zip(cells, owner):
        ordered[int(i)] = cell
    return ordered


def _single_polygon(geom):
    """Return ``geom`` as one non-empty Polygon, or None if it is not one.

    The intersection of two convex polygons is a single convex polygon, so a
    GeometryCollection may only carry stray lower-dimensional pieces alongside
    exactly one polygon; anything else signals a degenerate GEOS result.
    """
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    parts = [g for g in shapely.get_parts(geom) if g.geom_type == "Polygon" and not g.is_empty]
    return parts[0] if len(parts) == 1 else None


# --------------------------------------------------------------------------- #
# Fallback path: direct half-plane clipping
# --------------------------------------------------------------------------- #

def _cells_by_clipping(pts: np.ndarray, rect: Polygon) -> List[Polygon]:
    """Clip the rectangle by the perpendicular bisectors, one point at a time."""
    minx, miny, maxx, maxy = rect.bounds
    base = np.array([[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy]], dtype=float)

    cells: List[Polygon] = []
    for i, p in enumerate(pts):
        poly = base
        diff = pts - p
        d2 = np.einsum("ij,ij->i", diff, diff)
        for j in np.argsort(d2, kind="stable"):
            if j == i:
                continue
            # A site farther than twice the cell's radius about p cannot cut it.
            rel = poly - p
            reach = 4.0 * np.max(np.einsum("ij,ij->i", rel, rel))
            if d2[j] > reach:
                break
            poly = _clip_to_nearer_side(poly, p, pts[j])
        cells.append(Polygon(poly))
    return cells


def _clip_to_nearer_side(poly: np.ndarray, p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Keep the part of convex ``poly`` that is at least as close to p as to q."""
    axis = q - p
    f = (poly - (p + q) / 2.0) @ axis  # > 0 on q's side of the bisector
    keep = f <= 0.0
    if keep.all():
        return poly

    out = []
    k = len(poly)
    for a in range(k):
        b = (a + 1) % k
        if keep[a]:
            out.append(poly[a])
        if keep[a] != keep[b]:
            t = f[a] / (f[a] - f[b])
            out.append(poly[a] + t * (poly[b] - poly[a]))

    arr = np.array(out, dtype=float)
    if len(arr) > 1:
        dup = np.all(arr == np.roll(arr, -1, axis=0), axis=1)
        arr = arr[~dup]
    return arr