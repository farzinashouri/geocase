```python
"""Rectangle-clipped Voronoi cells for points in a projected (planar) CRS.

The only public entry point is :func:`voronoi_cells`, which returns one
:class:`shapely.geometry.Polygon` per input point, in input order.  Importing
this module has no side effects.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import MultiPoint, Polygon, box

__all__ = ["voronoi_cells"]

Point2D = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(
    points: Sequence[Point2D],
    bounds: Bounds,
) -> List[Polygon]:
    """Clip the Voronoi diagram of ``points`` to the rectangle ``bounds``.

    Parameters
    ----------
    points:
        ``N`` distinct ``(x, y)`` tuples in a projected (planar) coordinate
        system, all contained in ``bounds``.
    bounds:
        ``(minx, miny, maxx, maxy)`` of a non-degenerate rectangle.

    Returns
    -------
    list of shapely.geometry.Polygon
        ``N`` polygons; the i-th one is exactly the set of locations inside the
        rectangle that are strictly closer to ``points[i]`` than to any other
        input point (its closure, so adjacent cells share their boundaries).
        The polygons tile the rectangle and are returned in input order.
    """
    coords = _as_coords(points)
    rect, extent = _as_rectangles(bounds)

    if len(coords) == 0:
        return []

    _check_inside(coords, rect.bounds)
    _check_distinct(coords)

    if len(coords) == 1:
        return [rect]

    cells = _raw_cells(coords, extent)
    order = _match_cells_to_points(cells, coords)
    return [_clip(cells[j], rect) for j in order]


def _as_coords(points: Sequence[Point2D]) -> np.ndarray:
    """Validate the input points and return them as an ``(N, 2)`` float array."""
    coords = np.asarray(points, dtype=float)
    if coords.size == 0:
        return coords.reshape(0, 2)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must be finite")
    return coords


def _as_rectangles(bounds: Bounds) -> Tuple[Polygon, Polygon]:
    """Return the clipping rectangle and a padded one for the raw diagram."""
    try:
        minx, miny, maxx, maxy = (float(v) for v in bounds)
    except (TypeError, ValueError) as exc:
        raise ValueError("bounds must be (minx, miny, maxx, maxy)") from exc
    if not (np.isfinite([minx, miny, maxx, maxy]).all() and minx < maxx and miny < maxy):
        raise ValueError("bounds must be a finite, non-degenerate rectangle")

    # GEOS only builds cells out to a clipping envelope; padding it well past
    # the rectangle guarantees the raw cells cover every corner of `rect`.
    pad = max(maxx - minx, maxy - miny)
    rect = box(minx, miny, maxx, maxy)
    extent = box(minx - pad, miny - pad, maxx + pad, maxy + pad)
    return rect, extent


def _check_inside(coords: np.ndarray, rect_bounds: Bounds) -> None:
    minx, miny, maxx, maxy = rect_bounds
    tol = 1e-9 * max(maxx - minx, maxy - miny)
    outside = (
        (coords[:, 0] < minx - tol)
        | (coords[:, 0] > maxx + tol)
        | (coords[:, 1] < miny - tol)
        | (coords[:, 1] > maxy + tol)
    )
    if outside.any():
        raise ValueError(
            f"{int(outside.sum())} point(s) lie outside bounds; "
            "bounds must contain all points"
        )


def _check_distinct(coords: np.ndarray) -> None:
    if len(np.unique(coords, axis=0)) != len(coords):
        raise ValueError("points must be distinct")


def _raw_cells(coords: np.ndarray, extent: Polygon) -> List[Polygon]:
    """Unclipped Voronoi cells, in whatever order GEOS produces them."""
    diagram = shapely.voronoi_polygons(MultiPoint(coords), extend_to=extent)
    cells = list(shapely.get_parts(diagram))
    if len(cells) != len(coords):
        raise RuntimeError(
            f"expected {len(coords)} Voronoi cells, got {len(cells)}"
        )
    return cells


def _match_cells_to_points(cells: List[Polygon], coords: np.ndarray) -> List[int]:
    """Map each point index to the index of the cell it generated.

    Distinct points each lie in the interior of exactly one cell, so a spatial
    lookup is unambiguous; the greedy bookkeeping and the nearest-cell fallback
    only guard against coordinates degraded by floating-point noise.
    """
    n = len(coords)
    pts = shapely.points(coords)
    order = [-1] * n
    taken = [False] * n

    tree = STRtree(cells)
    src, tgt = tree.query(pts, predicate="intersects")
    for i, j in zip(src.tolist(), tgt.tolist()):
        if order[i] == -1 and not taken[j]:
            order[i] = j
            taken[j] = True

    unmatched = [i for i in range(n) if order[i] == -1]
    if unmatched:
        free = [j for j, used in enumerate(taken) if not used]
        for i in unmatched:
            k = int(np.argmin([shapely.distance(pts[i], cells[j]) for j in free]))
            order[i] = free.pop(k)
    return order


def _clip(cell: Polygon, rect: Polygon) -> Polygon:
    """Intersect a convex cell with the rectangle, as a single Polygon."""
    clipped = shapely.intersection(cell, rect)
    if isinstance(clipped, Polygon):
        return clipped
    # Convex ∩ convex is convex, so this is only reachable if robustness
    # fixes left slivers behind; keep the one piece with real area.
    parts = [g for g in shapely.get_parts(clipped) if isinstance(g, Polygon)]
    if not parts:
        raise RuntimeError("clipped Voronoi cell is empty")
    return max(parts, key=lambda g: g.area)
```