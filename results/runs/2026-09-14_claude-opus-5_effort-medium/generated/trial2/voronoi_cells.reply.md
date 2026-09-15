```python
"""Exact planar Voronoi cells, clipped to a bounding rectangle.

``voronoi_cells(points, bounds)`` returns one :class:`shapely.geometry.Polygon`
per input point, in input order, each being the set of locations inside
``bounds`` that are strictly closer to that point than to any other.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.strtree import STRtree

__all__ = ["voronoi_cells"]


def voronoi_cells(
    points: Iterable[Sequence[float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    """Return the Voronoi cell of each point, clipped to the ``bounds`` rectangle.

    Parameters
    ----------
    points:
        Iterable of ``N`` distinct ``(x, y)`` pairs in a projected (planar) CRS.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle containing all the points.

    Returns
    -------
    list of Polygon
        ``N`` polygons; element ``i`` corresponds to ``points[i]``.
    """
    coords = [(float(x), float(y)) for x, y in points]
    if not coords:
        return []

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if minx > maxx:
        minx, maxx = maxx, minx
    if miny > maxy:
        miny, maxy = maxy, miny
    rect = box(minx, miny, maxx, maxy)

    # A single site owns the whole rectangle; GEOS declines to build a diagram.
    if len(coords) == 1:
        return [rect]

    sites = MultiPoint(coords)

    # Unbounded cells are clipped by GEOS to the envelope of ``extend_to``, so
    # push that envelope well outside the rectangle to keep the clip a no-op
    # for the region we actually care about.
    span = max(maxx - minx, maxy - miny, 1.0)
    margin = 10.0 * span
    envelope = box(minx - margin, miny - margin, maxx + margin, maxy + margin)

    try:
        diagram = shapely.voronoi_polygons(
            sites, tolerance=0.0, extend_to=envelope, ordered=True
        )
        cells = list(diagram.geoms)
    except TypeError:
        # shapely < 2.1: no ``ordered`` keyword, so recover the order ourselves.
        diagram = shapely.voronoi_polygons(sites, tolerance=0.0, extend_to=envelope)
        cells = _match_to_points(list(diagram.geoms), coords)

    if len(cells) != len(coords):
        cells = _match_to_points(cells, coords)

    return [_clip(cell, rect) for cell in cells]


def _match_to_points(cells: List[Polygon], coords) -> List[Polygon]:
    """Reorder ``cells`` so that cell ``i`` is the one containing ``coords[i]``."""
    tree = STRtree(cells)
    ordered: List[Polygon] = []
    for xy in coords:
        site = Point(xy)
        hit = None
        for idx in tree.query(site):
            candidate = cells[idx]
            if candidate.covers(site):
                hit = candidate
                break
        if hit is None:
            # Site exactly on a shared edge (or float noise): take the nearest cell.
            hit = cells[min(range(len(cells)), key=lambda i: cells[i].distance(site))]
        ordered.append(hit)
    return ordered


def _clip(cell: Polygon, rect: Polygon) -> Polygon:
    """Intersect a (convex) Voronoi cell with the rectangle, as a single Polygon."""
    if not cell.is_valid:
        cell = cell.buffer(0)
    clipped = cell.intersection(rect)

    if isinstance(clipped, Polygon):
        return clipped
    if clipped.is_empty:
        return Polygon()

    # A convex cell met a rectangle, so anything other than one polygon is
    # numerical debris (slivers, stray lines): keep the largest polygonal part.
    parts = [g for g in getattr(clipped, "geoms", []) if isinstance(g, Polygon)]
    if not parts:
        return Polygon()
    return max(parts, key=lambda g: g.area)
```