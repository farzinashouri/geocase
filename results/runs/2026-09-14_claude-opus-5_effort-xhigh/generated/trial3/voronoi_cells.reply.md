```python
"""Exact Voronoi cells for planar points, clipped to a bounding rectangle.

The only public entry point is :func:`voronoi_cells`.  Importing this module
has no side effects.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon, box

__all__ = ["voronoi_cells"]

Point2D = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(points: Sequence[Point2D], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of every point, clipped to ``bounds``.

    Parameters
    ----------
    points:
        ``N`` distinct ``(x, y)`` pairs in a projected (planar) CRS, all of
        which must lie inside ``bounds``.
    bounds:
        ``(minx, miny, maxx, maxy)``, a rectangle of positive area.

    Returns
    -------
    list of shapely.Polygon
        One polygon per input point, in input order: ``result[i]`` is the part
        of the rectangle whose locations are closer to ``points[i]`` than to
        any other input point.  Cells are returned closed, so they tile the
        rectangle exactly and touch only along the bisectors they share.
    """
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or pts.shape[0] == 0:
        raise ValueError("points must be a non-empty sequence of (x, y) pairs")
    if not np.isfinite(pts).all():
        raise ValueError("points must be finite")
    if len(np.unique(pts, axis=0)) != len(pts):
        raise ValueError("points must be distinct")

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be (minx, miny, maxx, maxy) with positive area")
    if ((pts[:, 0] < minx).any() or (pts[:, 0] > maxx).any()
            or (pts[:, 1] < miny).any() or (pts[:, 1] > maxy).any()):
        raise ValueError("every point must lie inside bounds")

    rect = box(minx, miny, maxx, maxy)
    n = len(pts)
    if n == 1:
        return [rect]

    # GEOS hands the cells back in an arbitrary order, so each one has to be
    # matched to its generator: the generator of a cell is the input point
    # nearest to any interior point of that cell.  ``extend_to`` only widens
    # the clipping envelope of the diagram, so pad it well past the rectangle
    # and do the real clipping ourselves.
    pad = math.hypot(maxx - minx, maxy - miny)
    diagram = shapely.voronoi_polygons(
        shapely.multipoints(pts),
        extend_to=box(minx - pad, miny - pad, maxx + pad, maxy + pad),
    )
    cells = shapely.get_parts(diagram)

    result: List[Optional[Polygon]] = [None] * n
    if cells.size:
        owners = shapely.STRtree(shapely.points(pts)).nearest(
            shapely.point_on_surface(cells)
        )
        claims = np.bincount(owners, minlength=n)
        for cell, owner in zip(cells, owners):
            if claims[owner] == 1:  # ambiguous matches are recomputed below
                result[owner] = _polygonal(shapely.intersection(cell, rect))

    # Safety net for degenerate inputs: any generator without an unambiguous
    # cell gets one built directly from the bisector half-planes.
    for i, cell in enumerate(result):
        if cell is None:
            result[i] = _polygonal(_clip_to_halfplanes(i, pts, rect))
    return result


def _clip_to_halfplanes(i: int, pts: np.ndarray, rect: Polygon) -> Polygon:
    """Build the cell of ``pts[i]`` by intersecting every bisector half-plane."""
    minx, miny, maxx, maxy = rect.bounds
    # Every midpoint lies inside the rectangle, so a half-plane truncated this
    # far from its midpoint still covers the whole rectangle.
    span = 4.0 * math.hypot(maxx - minx, maxy - miny)
    cell = rect
    for j in range(len(pts)):
        if j == i:
            continue
        cell = cell.intersection(_halfplane(pts[i], pts[j], span))
        if cell.is_empty:
            break
    return cell


def _halfplane(p: np.ndarray, q: np.ndarray, span: float) -> Polygon:
    """Polygon covering ``{x : |x - p| <= |x - q|}`` within ``span`` of the midpoint."""
    dx, dy = float(q[0] - p[0]), float(q[1] - p[1])
    length = math.hypot(dx, dy)
    if length == 0.0:
        raise ValueError("points must be distinct")
    nx, ny = dx / length, dy / length          # unit normal, pointing from p to q
    tx, ty = -ny, nx                           # along the bisector
    mx, my = (p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0
    ax, ay = mx + span * tx, my + span * ty
    bx, by = mx - span * tx, my - span * ty
    return Polygon([
        (ax, ay),
        (bx, by),
        (bx - 2.0 * span * nx, by - 2.0 * span * ny),
        (ax - 2.0 * span * nx, ay - 2.0 * span * ny),
    ])


def _polygonal(geom) -> Polygon:
    """Coerce a clipped cell to a single non-empty ``Polygon``."""
    if isinstance(geom, Polygon) and not geom.is_empty:
        return geom
    parts = [
        g for g in getattr(geom, "geoms", ())
        if isinstance(g, Polygon) and not g.is_empty
    ]
    if not parts:
        raise RuntimeError(f"Voronoi cell is not polygonal: {geom.geom_type}")
    return max(parts, key=lambda g: g.area)
```