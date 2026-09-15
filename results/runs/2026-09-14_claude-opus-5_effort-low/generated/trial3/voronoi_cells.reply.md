```python
"""Bounded Voronoi (nearest-neighbour) cells for planar points.

``voronoi_cells(points, bounds)`` returns one polygon per input point: the set
of locations inside ``bounds`` that are strictly closer to that point than to
any other input point (boundaries between cells are shared by the neighbours).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import MultiPoint, Polygon, box

__all__ = ["voronoi_cells"]

Point2D = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(
    points: Iterable[Point2D],
    bounds: Bounds,
) -> List[Polygon]:
    """Clip the Voronoi diagram of ``points`` to the rectangle ``bounds``.

    Parameters
    ----------
    points:
        ``N`` distinct ``(x, y)`` tuples in a projected (planar) CRS.
    bounds:
        ``(minx, miny, maxx, maxy)``; must contain every point.

    Returns
    -------
    list of shapely.Polygon
        The i-th polygon is the cell of the i-th input point, in input order.
    """
    coords: Sequence[Point2D] = [(float(x), float(y)) for x, y in points]
    if not coords:
        return []

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if minx >= maxx or miny >= maxy:
        raise ValueError("bounds must be a non-degenerate rectangle")
    envelope = box(minx, miny, maxx, maxy)

    for x, y in coords:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x}, {y}) lies outside bounds")

    if len(set(coords)) != len(coords):
        raise ValueError("points must be distinct")

    # A single point owns the whole rectangle; shapely returns nothing for it.
    if len(coords) == 1:
        return [envelope]

    sites = MultiPoint(coords)
    # ordered=True (shapely >= 2.1) keeps cell i aligned with point i.
    cells = shapely.voronoi_polygons(sites, extend_to=envelope, ordered=True)

    clipped: List[Polygon] = []
    for cell in shapely.get_parts(cells):
        piece = cell.intersection(envelope)
        # Voronoi cells and the rectangle are both convex, so the intersection
        # is a single (possibly empty) convex polygon.
        if piece.is_empty or not isinstance(piece, Polygon):
            raise RuntimeError("unexpected Voronoi cell geometry after clipping")
        clipped.append(piece)

    if len(clipped) != len(coords):
        raise RuntimeError(
            f"expected {len(coords)} Voronoi cells, got {len(clipped)}"
        )
    return clipped
```