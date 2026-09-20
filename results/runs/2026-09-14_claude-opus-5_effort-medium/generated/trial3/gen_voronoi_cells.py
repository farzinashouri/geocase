"""Exact planar Voronoi cells, clipped to a bounding rectangle.

Given N distinct points in a projected (planar) coordinate system and a
rectangle containing them, :func:`voronoi_cells` returns N polygons, the
i-th being exactly the set of locations inside the rectangle that are
closer to ``points[i]`` than to any other input point.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import MultiPoint, Point, Polygon, box

__all__ = ["voronoi_cells"]

Coord = Tuple[float, float]


def voronoi_cells(
    points: Sequence[Coord], bounds: Tuple[float, float, float, float]
) -> List[Polygon]:
    """Return the bounded Voronoi cell of each input point.

    Parameters
    ----------
    points:
        Sequence of N distinct ``(x, y)`` tuples in a planar CRS.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle containing every point.

    Returns
    -------
    list of shapely.geometry.Polygon
        ``result[i]`` is ``rectangle ∩ {p : |p - points[i]| < |p - points[j]| for all j != i}``,
        i.e. the cells are in the same order as ``points``, tile the
        rectangle, and overlap only along their shared boundaries.
    """
    coords = _validate_points(points)
    rect = _validate_bounds(bounds, coords)

    if len(coords) == 1:
        return [rect]

    # A Voronoi diagram of points lying strictly inside `rect` can have
    # unbounded cells; `extend_to` forces the construction region to be at
    # least as large as the padded envelope so every cell fully covers its
    # share of `rect` before clipping.
    region = _padded_region(rect, coords)
    multipoint = MultiPoint([Point(x, y) for x, y in coords])

    try:
        raw = shapely.voronoi_polygons(multipoint, extend_to=region, ordered=True)
        cells = list(shapely.get_parts(raw))
        if len(cells) != len(coords):
            raise ValueError("unexpected cell count")
    except (TypeError, ValueError):
        # shapely < 2.1 has no `ordered` keyword, or GEOS dropped/merged a
        # cell; fall back to matching each cell to the point it contains.
        raw = shapely.voronoi_polygons(multipoint, extend_to=region)
        cells = _match_cells_to_points(list(shapely.get_parts(raw)), coords)

    return [_clip(cell, rect) for cell in cells]


def _validate_points(points: Iterable[Coord]) -> List[Coord]:
    coords = [(float(x), float(y)) for x, y in points]
    if not coords:
        raise ValueError("points must contain at least one point")
    if len(set(coords)) != len(coords):
        raise ValueError("points must be distinct")
    return coords


def _validate_bounds(
    bounds: Tuple[float, float, float, float], coords: Sequence[Coord]
) -> Polygon:
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be a non-degenerate (minx, miny, maxx, maxy)")
    for x, y in coords:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x}, {y}) lies outside bounds")
    return box(minx, miny, maxx, maxy)


def _padded_region(rect: Polygon, coords: Sequence[Coord]) -> Polygon:
    """An envelope comfortably larger than the rectangle and the points."""
    minx, miny, maxx, maxy = rect.bounds
    pad = max(maxx - minx, maxy - miny)
    if pad <= 0.0:  # pragma: no cover - guarded by _validate_bounds
        pad = 1.0
    return box(minx - pad, miny - pad, maxx + pad, maxy + pad)


def _match_cells_to_points(
    cells: Sequence[Polygon], coords: Sequence[Coord]
) -> List[Polygon]:
    """Reorder `cells` so that cell i contains coords[i]."""
    tree = shapely.STRtree(cells)
    pts = shapely.points([[x, y] for x, y in coords])
    ordered: List[Polygon] = []
    for i, pt in enumerate(pts):
        candidates = tree.query(pt, predicate="intersects")
        if len(candidates) == 0:
            raise ValueError(f"no Voronoi cell found for point {coords[i]}")
        if len(candidates) == 1:
            ordered.append(cells[int(candidates[0])])
            continue
        # Ties (a point exactly on a shared edge) are resolved by distance
        # from the cell's interior representative point.
        best = min(
            (int(j) for j in candidates),
            key=lambda j: shapely.distance(
                shapely.point_on_surface(cells[j]), pt
            ),
        )
        ordered.append(cells[best])
    return ordered


def _clip(cell: Polygon, rect: Polygon) -> Polygon:
    """Intersect a (convex) Voronoi cell with the rectangle."""
    clipped = shapely.intersection(cell, rect)
    if isinstance(clipped, Polygon):
        return clipped
    # Both operands are convex, so a non-polygonal result can only come from
    # numerical noise (slivers, touching-only pieces); keep the largest part.
    parts = [g for g in shapely.get_parts(clipped) if isinstance(g, Polygon)]
    if not parts:
        return Polygon()
    return max(parts, key=lambda g: g.area)