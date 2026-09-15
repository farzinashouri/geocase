```python
"""Exact Voronoi cells of a point set, clipped to a bounding rectangle.

``voronoi_cells(points, bounds)`` returns one :class:`shapely.Polygon` per input
point, *in input order*, each being the part of the ``bounds`` rectangle whose
locations are closer to that point than to any other input point.

Two things make this less trivial than a single call into GEOS:

* ``shapely.voronoi_polygons`` returns the cells in an unspecified order that
  does **not** follow the input points, so the cells have to be matched back to
  their sites (each site lies in the interior of exactly one unclipped cell).
* GEOS clips the diagram to an envelope of its own choosing, so the cells must
  still be intersected with the requested rectangle.

The GEOS path is used when it produces a clean one-cell-per-site diagram;
otherwise (single point, collinear sites, and other degenerate configurations
GEOS declines to triangulate) the module falls back to an exact half-plane
construction: a cell is the rectangle clipped by the perpendicular bisector
against every other site. Both paths yield convex polygons that tile the
rectangle.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np
import shapely
from shapely import Polygon

__all__ = ["voronoi_cells"]

Point2D = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(points: Sequence[Point2D], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of each point, clipped to ``bounds``.

    Parameters
    ----------
    points:
        ``N`` distinct ``(x, y)`` pairs in a projected (planar) CRS, all inside
        ``bounds``.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle containing every point.

    Returns
    -------
    list of shapely.Polygon
        ``N`` convex polygons, the i-th being the locus of points of the
        rectangle nearest to ``points[i]``. The cells tile the rectangle and
        overlap only along shared edges.
    """
    coords = np.asarray(points, dtype=float)
    if coords.ndim != 2 or coords.shape[0] == 0 or coords.shape[1] != 2:
        raise ValueError("points must be a non-empty sequence of (x, y) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must be finite")
    if len(np.unique(coords, axis=0)) != len(coords):
        raise ValueError("points must be distinct")

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be a non-degenerate (minx, miny, maxx, maxy) rectangle")

    # Points on the rectangle boundary are fine; guard only against real strays.
    tol = 1e-9 * max(maxx - minx, maxy - miny)
    if (
        (coords[:, 0] < minx - tol).any()
        or (coords[:, 0] > maxx + tol).any()
        or (coords[:, 1] < miny - tol).any()
        or (coords[:, 1] > maxy + tol).any()
    ):
        raise ValueError("every point must lie inside bounds")

    rect = shapely.box(minx, miny, maxx, maxy)
    if len(coords) == 1:
        return [rect]

    cells = _cells_via_geos(coords, rect)
    if cells is None:
        cells = _cells_via_half_planes(coords, rect)
    return cells


def _cells_via_geos(coords: np.ndarray, rect: Polygon) -> "List[Polygon] | None":
    """Fast path through GEOS; returns ``None`` if the diagram is unusable."""
    minx, miny, maxx, maxy = rect.bounds
    pad = max(maxx - minx, maxy - miny)
    # Extend past the rectangle so every site stays strictly interior to its
    # own cell, which is what makes the site -> cell matching below unambiguous.
    frame = shapely.box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    try:
        diagram = shapely.voronoi_polygons(shapely.MultiPoint(coords), extend_to=frame)
        parts = [g for g in shapely.get_parts(diagram) if isinstance(g, Polygon)]
        if len(parts) != len(coords):
            return None

        tree = shapely.STRtree(parts)
        sites = shapely.points(coords)
        site_idx, part_idx = np.asarray(tree.query(sites, predicate="contains"))
        if len(site_idx) != len(coords) or len(np.unique(site_idx)) != len(coords):
            return None

        owner = np.empty(len(coords), dtype=np.int64)
        owner[site_idx] = part_idx
        if len(np.unique(owner)) != len(coords):
            return None

        cells = []
        for i in range(len(coords)):
            cell = _as_polygon(rect.intersection(parts[owner[i]]))
            if cell is None:
                return None
            cells.append(cell)
        return cells
    except Exception:
        return None


def _cells_via_half_planes(coords: np.ndarray, rect: Polygon) -> List[Polygon]:
    """Exact construction: clip the rectangle by every perpendicular bisector."""
    minx, miny, maxx, maxy = rect.bounds
    corners = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)]
    xs = coords[:, 0]
    ys = coords[:, 1]

    cells: List[Polygon] = []
    for i in range(len(coords)):
        xi = float(xs[i])
        yi = float(ys[i])
        dist = np.hypot(xs - xi, ys - yi)
        ring = list(corners)
        radius = _max_radius(ring, xi, yi)

        # Nearest sites first: once a site is at least 2 * radius away its
        # bisector lies beyond the cell and neither it nor any farther site
        # can cut anything off.
        for j in np.argsort(dist, kind="stable"):
            if j == i:
                continue
            if dist[j] >= 2.0 * radius:
                break
            xj = float(xs[j])
            yj = float(ys[j])
            nx = xj - xi
            ny = yj - yi
            offset = nx * (xi + xj) * 0.5 + ny * (yi + yj) * 0.5
            ring = _clip_half_plane(ring, nx, ny, offset)
            if len(ring) < 3:
                break
            radius = _max_radius(ring, xi, yi)

        cells.append(Polygon(ring) if len(ring) >= 3 else Polygon())
    return cells


def _clip_half_plane(
    ring: List[Point2D], nx: float, ny: float, offset: float
) -> List[Point2D]:
    """Sutherland-Hodgman clip of a convex ring to ``nx*x + ny*y <= offset``."""
    out: List[Point2D] = []
    n = len(ring)
    for k in range(n):
        ax, ay = ring[k]
        bx, by = ring[(k + 1) % n]
        fa = nx * ax + ny * ay - offset
        fb = nx * bx + ny * by - offset
        if fa <= 0.0:
            _push(out, ax, ay)
        if (fa < 0.0 < fb) or (fb < 0.0 < fa):
            t = fa / (fa - fb)
            _push(out, ax + t * (bx - ax), ay + t * (by - ay))
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _push(ring: List[Point2D], x: float, y: float) -> None:
    if not ring or ring[-1] != (x, y):
        ring.append((x, y))


def _max_radius(ring: Sequence[Point2D], x: float, y: float) -> float:
    return max(math.hypot(px - x, py - y) for px, py in ring)


def _as_polygon(geom) -> "Polygon | None":
    """Normalise an intersection result to a single non-empty Polygon."""
    if geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    polygons = [g for g in shapely.get_parts(geom) if isinstance(g, Polygon) and not g.is_empty]
    if not polygons:
        return None
    return max(polygons, key=lambda g: g.area)
```