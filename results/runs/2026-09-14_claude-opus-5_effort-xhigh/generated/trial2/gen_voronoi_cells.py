"""Exact Voronoi tessellation of a rectangle over a set of planar sites.

``voronoi_cells(points, bounds)`` returns one shapely ``Polygon`` per input
point: the part of the ``bounds`` rectangle that is closer to that point than to
any other input point.  Cells are closed sets, so neighbouring cells share their
common boundary edge exactly and together they tile ``bounds`` with no gaps and
no overlapping interiors.

Only shapely (GEOS) is used, so cell edges are computed from the Delaunay
triangulation rather than sampled or approximated.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import shapely
from shapely import STRtree
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["voronoi_cells"]

Coordinate = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(points: Sequence[Coordinate], bounds: Bounds) -> List[Polygon]:
    """Split ``bounds`` into the Voronoi cells of ``points``.

    Parameters
    ----------
    points:
        ``N`` distinct ``(x, y)`` tuples in a projected (planar) coordinate
        system, all inside ``bounds``.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle containing every point.

    Returns
    -------
    list of :class:`shapely.geometry.Polygon`
        ``N`` polygons, the i-th being the locations in ``bounds`` at least as
        close to ``points[i]`` as to any other input point.

    Raises
    ------
    ValueError
        If ``bounds`` is malformed, a point lies outside ``bounds``, the points
        are not distinct, or two or more points must share a zero-area
        rectangle.
    """
    sites = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(value) for value in bounds)

    if minx > maxx or miny > maxy:
        raise ValueError(
            "bounds must be (minx, miny, maxx, maxy) with minx <= maxx and miny <= maxy"
        )
    if not sites:
        return []
    if len(set(sites)) != len(sites):
        raise ValueError("points must be distinct")
    for x, y in sites:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x}, {y}) lies outside bounds")

    rectangle = box(minx, miny, maxx, maxy)
    if len(sites) == 1:
        return [rectangle]
    if minx == maxx or miny == maxy:
        raise ValueError("bounds must enclose a positive area to divide between 2+ points")

    # GEOS grows the diagram to cover ``extend_to``'s envelope, so every cell
    # reaches past the rectangle and the clip below cannot truncate a cell short
    # of the rectangle's edge.
    diagram = shapely.voronoi_polygons(MultiPoint(sites), extend_to=rectangle)
    cells = [_as_polygon(shapely.intersection(cell, rectangle)) for cell in diagram.geoms]

    # GEOS emits the cells in its own order (shapely's ``ordered=True`` needs
    # GEOS >= 3.12), so pair each cell back with the site that generated it.
    # Distinct sites lie strictly inside their own cell, which makes the match
    # unambiguous.
    tree = STRtree(cells)
    owners = [_owning_cell(tree, cells, Point(site)) for site in sites]
    if len(set(owners)) != len(sites):
        raise RuntimeError("failed to match Voronoi cells back to their input points")
    return [cells[index] for index in owners]


def _owning_cell(tree: STRtree, cells: Sequence[Polygon], site: Point) -> int:
    """Index of the cell containing ``site``."""
    hits = [int(index) for index in tree.query(site, predicate="intersects")]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        return int(tree.nearest(site))
    # Rounding can put a site exactly on a shared edge; prefer the cell whose
    # interior it sits furthest inside.
    return max(hits, key=lambda index: cells[index].boundary.distance(site))


def _as_polygon(geometry: BaseGeometry) -> Polygon:
    """Coerce a clipped cell to a single ``Polygon``."""
    if isinstance(geometry, Polygon):
        return geometry
    parts = [part for part in getattr(geometry, "geoms", ()) if isinstance(part, Polygon)]
    if not parts:
        raise RuntimeError("clipping a Voronoi cell to the bounds produced no polygon")
    return max(parts, key=lambda part: part.area)