# voronoi_cells.py
"""
A small module that provides a function to compute clipped Voronoi cells
for a set of points within a bounding rectangle.

Dependencies: shapely 2.1
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from shapely.geometry import Point, box, Polygon
from shapely.ops import voronoi_diagram


def voronoi_cells(
    points: Iterable[Tuple[float, float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    """
    Return a list of Voronoi polygons clipped to the given bounds.

    Parameters
    ----------
    points:
        An iterable of (x, y) tuples. All points must be distinct and lie
        within the bounding rectangle.
    bounds:
        A tuple (minx, miny, maxx, maxy) defining a rectangle that contains
        all points.

    Returns
    -------
    List[Polygon]
        A list of shapely Polygon objects. The i-th polygon corresponds to
        the i-th point in the input sequence and represents the region of
        the rectangle that is closer to that point than to any other point.
    """
    minx, miny, maxx, maxy = bounds
    bbox = box(minx, miny, maxx, maxy)

    # Convert input points to shapely Points
    shapely_points: List[Point] = [Point(p) for p in points]

    # Compute the Voronoi diagram clipped to the bounding box
    diagram = voronoi_diagram(shapely_points, envelope=bbox, tolerance=1e-12)

    # For each input point, find the polygon that contains it.
    # Use `covers` to handle points that lie on polygon boundaries.
    cells: List[Polygon] = []
    for pt in shapely_points:
        cell = None
        for geom in diagram.geoms:
            if geom.covers(pt):
                cell = geom
                break
        # In the unlikely event that no polygon covers the point,
        # fall back to the bounding box (should not happen with valid input).
        if cell is None:
            cell = bbox
        cells.append(cell)

    return cells