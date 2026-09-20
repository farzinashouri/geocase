```python
"""Bounded Voronoi tessellation of a set of planar points.

``voronoi_cells(points, bounds)`` partitions a rectangle into the nearest-point
regions of the given sites, returning one polygon per input point, in input
order.  Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import GeometryCollection, MultiPoint, MultiPolygon, Point, Polygon, box
from shapely.strtree import STRtree

__all__ = ["voronoi_cells"]


def voronoi_cells(
    points: Iterable[Sequence[float]],
    bounds: Sequence[float],
) -> List[Polygon]:
    """Clip the Voronoi diagram of ``points`` to the rectangle ``bounds``.

    Parameters
    ----------
    points:
        Iterable of N distinct ``(x, y)`` pairs in a projected (planar) CRS.
    bounds:
        Rectangle ``(minx, miny, maxx, maxy)`` containing every point.

    Returns
    -------
    list of shapely.geometry.Polygon
        ``result[i]`` is exactly the set of locations inside the rectangle that
        are strictly closer to ``points[i]`` than to any other input point
        (closed up, so adjacent cells share their boundary edges).  The cells
        cover the rectangle and have pairwise-disjoint interiors.
    """
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be (minx, miny, maxx, maxy) with minx < maxx and miny < maxy")

    sites: List[Tuple[float, float]] = [(float(x), float(y)) for x, y in points]
    if not sites:
        return []
    if len(set(sites)) != len(sites):
        raise ValueError("points must be distinct")
    for x, y in sites:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x}, {y}) lies outside bounds")

    rect = box(minx, miny, maxx, maxy)

    # A single site owns the whole rectangle; shapely would return no cells.
    if len(sites) == 1:
        return [rect]

    # Force every cell to reach past the rectangle so that clipping, rather than
    # shapely's own default envelope, decides the outer boundary.
    margin = max(maxx - minx, maxy - miny)
    extent = box(minx - margin, miny - margin, maxx + margin, maxy + margin)

    multipoint = MultiPoint(sites)
    ordered_cells = None
    try:
        # shapely >= 2.1 can return cells aligned with the input point order.
        ordered_cells = shapely.voronoi_polygons(multipoint, extend_to=extent, ordered=True)
    except TypeError:
        ordered_cells = None

    if ordered_cells is not None and len(ordered_cells.geoms) == len(sites):
        raw = list(ordered_cells.geoms)
    else:
        raw = _match_cells_to_sites(
            list(shapely.voronoi_polygons(multipoint, extend_to=extent).geoms), sites
        )

    return [_clip(cell, rect, site) for cell, site in zip(raw, sites)]


def _match_cells_to_sites(cells, sites):
    """Reorder unordered Voronoi cells so that cell ``i`` contains ``sites[i]``."""
    tree = STRtree(cells)
    matched = [None] * len(sites)
    used = set()
    for i, site in enumerate(sites):
        pt = Point(site)
        candidates = [j for j in tree.query(pt) if j not in used and cells[j].covers(pt)]
        if not candidates:
            # Numerical edge case: fall back to the closest unused cell.
            candidates = [
                min(
                    (j for j in range(len(cells)) if j not in used),
                    key=lambda j: cells[j].distance(pt),
                )
            ]
        j = candidates[0]
        used.add(j)
        matched[i] = cells[j]
    return matched


def _clip(cell, rect, site) -> Polygon:
    """Intersect a (convex, unbounded-then-extended) cell with the rectangle."""
    clipped = cell.intersection(rect)
    if isinstance(clipped, Polygon):
        return clipped
    if isinstance(clipped, (MultiPolygon, GeometryCollection)):
        parts = [g for g in clipped.geoms if isinstance(g, Polygon) and not g.is_empty]
        if parts:
            pt = Point(site)
            covering = [g for g in parts if g.covers(pt)]
            return max(covering or parts, key=lambda g: g.area)
    # Degenerate slivers (lines/points) carry no area; report them as empty.
    return Polygon()
```