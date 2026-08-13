"""Bounded Voronoi diagrams.

Provides :func:`voronoi_cells`, which computes the Voronoi cell of each
input point clipped to a rectangular boundary, returned in the same order
as the input points.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np
from shapely import MultiPoint, box, voronoi_polygons
from shapely.geometry import Polygon

__all__ = ["voronoi_cells"]


def voronoi_cells(
    points: Sequence[Tuple[float, float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    """Compute Voronoi cells of ``points`` clipped to a rectangle.

    Parameters
    ----------
    points:
        A list of N distinct ``(x, y)`` tuples in a projected (planar)
        coordinate system.
    bounds:
        A rectangle ``(minx, miny, maxx, maxy)`` that contains all points.

    Returns
    -------
    list of shapely.geometry.Polygon
        N polygons; the i-th polygon is exactly the part of the rectangle
        consisting of the locations closer to ``points[i]`` than to any
        other input point.
    """
    pts = list(points)
    n = len(pts)
    if n == 0:
        return []

    minx, miny, maxx, maxy = bounds
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must describe a non-degenerate rectangle")
    rect = box(minx, miny, maxx, maxy)

    if n == 1:
        return [rect]

    coords = np.asarray(pts, dtype=float)
    if coords.shape != (n, 2):
        raise ValueError("points must be a sequence of (x, y) pairs")

    # Build the Voronoi diagram over an envelope comfortably larger than the
    # clipping rectangle so that every cell fully covers its share of it.
    pad = 2.0 * max(maxx - minx, maxy - miny)
    envelope = box(minx - pad, miny - pad, maxx + pad, maxy + pad)
    diagram = voronoi_polygons(MultiPoint(coords), extend_to=envelope)

    # Map each raw cell back to the index of its generating point: any
    # interior point of a Voronoi cell is strictly closer to its generator
    # than to every other input point.
    result: List[Polygon] = [None] * n  # type: ignore[list-item]
    for cell in diagram.geoms:
        rep = cell.representative_point()
        d2 = (coords[:, 0] - rep.x) ** 2 + (coords[:, 1] - rep.y) ** 2
        idx = int(np.argmin(d2))
        if result[idx] is not None:
            raise ValueError("points must be distinct")
        clipped = cell.intersection(rect)
        if not isinstance(clipped, Polygon):
            # Voronoi cells and the rectangle are convex, so this only
            # happens for degenerate (lower-dimensional) intersections.
            clipped = Polygon()
        result[idx] = clipped

    missing = [i for i, cell in enumerate(result) if cell is None]
    if missing:
        raise ValueError("points must be distinct")
    return result
