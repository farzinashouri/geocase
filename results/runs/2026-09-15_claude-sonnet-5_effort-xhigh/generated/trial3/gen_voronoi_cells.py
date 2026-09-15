"""Compute Voronoi cells for a set of planar points, clipped to a rectangle."""

from shapely.geometry import MultiPoint, Point, box
from shapely.ops import voronoi_diagram


def voronoi_cells(points, bounds):
    points = list(points)
    minx, miny, maxx, maxy = bounds
    rectangle = box(minx, miny, maxx, maxy)

    n = len(points)
    if n == 0:
        return []
    if n == 1:
        return [rectangle]

    diagram = voronoi_diagram(MultiPoint(points), envelope=rectangle)
    cells = list(diagram.geoms)

    # voronoi_diagram does not guarantee its output order matches the input
    # point order, so match each cell back to the point it was generated
    # from (a point always lies in the interior of its own cell, or on its
    # boundary if it lies on the rectangle's boundary, giving it distance 0).
    remaining = list(range(len(cells)))
    result = [None] * n
    for i, coords in enumerate(points):
        seed = Point(coords)
        match = next((j for j in remaining if cells[j].contains(seed)), None)
        if match is None:
            match = min(remaining, key=lambda j: cells[j].distance(seed))
        remaining.remove(match)
        result[i] = cells[match].intersection(rectangle)

    return result