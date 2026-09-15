"""Compute Voronoi cells for a set of points clipped to a rectangle."""

from typing import List, Tuple

from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import voronoi_diagram


def voronoi_cells(
    points: List[Tuple[float, float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    minx, miny, maxx, maxy = bounds
    rect = box(minx, miny, maxx, maxy)

    if len(points) == 1:
        return [rect]

    diagram = voronoi_diagram(MultiPoint(points), envelope=rect)
    clipped_cells = [cell.intersection(rect) for cell in diagram.geoms]

    result: List[Polygon] = [None] * len(points)
    remaining_cells = list(clipped_cells)
    for i, coords in enumerate(points):
        pt = Point(coords)
        for j, cell in enumerate(remaining_cells):
            if cell is not None and cell.intersects(pt):
                result[i] = cell
                remaining_cells[j] = None
                break

    return result