"""Exact Voronoi cells for planar points, clipped to a bounding rectangle.

The public entry point is :func:`voronoi_cells`.  Importing this module has no
side effects.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import Polygon, box
from shapely.errors import ShapelyError

__all__ = ["voronoi_cells"]

Point2D = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(
    points: Sequence[Point2D],
    bounds: Bounds,
) -> List[Polygon]:
    """Return the Voronoi cells of ``points`` clipped to ``bounds``.

    Parameters
    ----------
    points:
        Sequence of ``N`` distinct ``(x, y)`` pairs in a projected (planar)
        coordinate system.
    bounds:
        Rectangle ``(minx, miny, maxx, maxy)`` containing every point.

    Returns
    -------
    list of shapely.Polygon
        ``N`` polygons in input order.  The i-th polygon is exactly the set of
        locations in the rectangle that are closer to ``points[i]`` than to any
        other input point: the cells are convex, have disjoint interiors, and
        their union is the whole rectangle.

    Raises
    ------
    ValueError
        If the points are not finite ``(x, y)`` pairs, are not distinct, if the
        rectangle is degenerate, or if a point lies outside the rectangle.
    """
    sites = _validate_points(points)
    rect = _validate_bounds(bounds, sites)
    if len(sites) == 0:
        return []

    # Fast path: one Delaunay-based diagram from GEOS, matched back to the input
    # order.  Anything GEOS declines to answer for falls back to the exact
    # half-plane construction below.
    diagram = _geos_cells(sites, rect)

    cells: List[Polygon] = []
    for index in range(len(sites)):
        cell: Optional[Polygon] = None
        if diagram[index] is not None:
            cell = _largest_polygon(shapely.intersection(diagram[index], rect))
        if cell is None or cell.is_empty:
            cell = _bisector_cell(sites, index, rect)
        cells.append(cell)
    return cells


# --------------------------------------------------------------------------- #
# input validation
# --------------------------------------------------------------------------- #


def _validate_points(points: Sequence[Point2D]) -> np.ndarray:
    array = np.asarray(points, dtype=float)
    if array.size == 0:
        return array.reshape(0, 2)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")
    if not np.isfinite(array).all():
        raise ValueError("points must have finite coordinates")
    if len(np.unique(array, axis=0)) != len(array):
        raise ValueError("points must be distinct")
    return array


def _validate_bounds(bounds: Bounds, sites: np.ndarray) -> Polygon:
    try:
        minx, miny, maxx, maxy = (float(value) for value in bounds)
    except (TypeError, ValueError) as exc:
        raise ValueError("bounds must be (minx, miny, maxx, maxy)") from exc
    if not all(np.isfinite([minx, miny, maxx, maxy])):
        raise ValueError("bounds must be finite")
    if minx >= maxx or miny >= maxy:
        raise ValueError("bounds must satisfy minx < maxx and miny < maxy")
    if len(sites):
        inside = (
            (sites[:, 0] >= minx)
            & (sites[:, 0] <= maxx)
            & (sites[:, 1] >= miny)
            & (sites[:, 1] <= maxy)
        )
        if not inside.all():
            raise ValueError("every point must lie inside bounds")
    return box(minx, miny, maxx, maxy)


# --------------------------------------------------------------------------- #
# GEOS diagram, re-ordered to match the input
# --------------------------------------------------------------------------- #


def _geos_cells(sites: np.ndarray, rect: Polygon) -> List[Optional[Polygon]]:
    """Unclipped GEOS Voronoi cells, indexed by input point (None if unmatched)."""
    cells: List[Optional[Polygon]] = [None] * len(sites)
    if len(sites) < 2:
        return cells

    # Pad the clip envelope so that every site — including any sitting on the
    # rectangle's edge — is strictly interior to its own cell.
    minx, miny, maxx, maxy = rect.bounds
    pad = max(maxx - minx, maxy - miny)
    envelope = box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    site_geoms = shapely.points(sites)
    try:
        diagram = shapely.voronoi_polygons(
            shapely.multipoints(site_geoms), extend_to=envelope
        )
    except (ShapelyError, ValueError, TypeError):
        return cells

    polygons = _polygons(diagram)
    if not polygons:
        return cells

    # GEOS does not promise cell order, so pair each site with the cell that
    # strictly contains it.
    tree = shapely.STRtree(polygons)
    site_index, cell_index = tree.query(site_geoms, predicate="contains")
    taken = set()
    for i, j in zip(site_index.tolist(), cell_index.tolist()):
        if cells[i] is None and j not in taken:
            cells[i] = polygons[j]
            taken.add(j)
    return cells


def _polygons(geometry) -> List[Polygon]:
    if isinstance(geometry, Polygon):
        return [] if geometry.is_empty else [geometry]
    parts: List[Polygon] = []
    for part in getattr(geometry, "geoms", ()):
        parts.extend(_polygons(part))
    return parts


def _largest_polygon(geometry) -> Polygon:
    parts = _polygons(geometry)
    if not parts:
        return Polygon()
    return max(parts, key=lambda part: part.area)


# --------------------------------------------------------------------------- #
# exact fallback: clip the rectangle by every perpendicular bisector
# --------------------------------------------------------------------------- #


def _bisector_cell(sites: np.ndarray, index: int, rect: Polygon) -> Polygon:
    """Cell of ``sites[index]`` built directly from the half-plane definition."""
    ring = [(float(x), float(y)) for x, y in rect.exterior.coords[:-1]]
    px, py = float(sites[index, 0]), float(sites[index, 1])

    for other in range(len(sites)):
        if other == index:
            continue
        qx, qy = float(sites[other, 0]), float(sites[other, 1])
        # Keep the side of the bisector holding p: (v - midpoint) . (q - p) <= 0.
        ring = _clip_halfplane(
            ring, qx - px, qy - py, 0.5 * (px + qx), 0.5 * (py + qy)
        )
        if len(ring) < 3:
            return Polygon()

    minx, miny, maxx, maxy = rect.bounds
    ring = _drop_repeats(ring, 1e-12 * max(maxx - minx, maxy - miny))
    return Polygon(ring) if len(ring) >= 3 else Polygon()


def _clip_halfplane(
    ring: List[Point2D], ax: float, ay: float, mx: float, my: float
) -> List[Point2D]:
    """Sutherland-Hodgman clip of a convex ring against ``a . (v - m) <= 0``."""
    values = [ax * (x - mx) + ay * (y - my) for x, y in ring]
    count = len(ring)
    kept: List[Point2D] = []
    for k in range(count):
        cur, f_cur = ring[k], values[k]
        nxt, f_nxt = ring[(k + 1) % count], values[(k + 1) % count]
        if f_cur <= 0.0:
            kept.append(cur)
        if (f_cur < 0.0 < f_nxt) or (f_nxt < 0.0 < f_cur):
            t = f_cur / (f_cur - f_nxt)
            kept.append((cur[0] + t * (nxt[0] - cur[0]), cur[1] + t * (nxt[1] - cur[1])))
    return kept


def _drop_repeats(ring: List[Point2D], tol: float) -> List[Point2D]:
    cleaned: List[Point2D] = []
    for x, y in ring:
        if cleaned and abs(x - cleaned[-1][0]) <= tol and abs(y - cleaned[-1][1]) <= tol:
            continue
        cleaned.append((x, y))
    while (
        len(cleaned) > 1
        and abs(cleaned[0][0] - cleaned[-1][0]) <= tol
        and abs(cleaned[0][1] - cleaned[-1][1]) <= tol
    ):
        cleaned.pop()
    return cleaned