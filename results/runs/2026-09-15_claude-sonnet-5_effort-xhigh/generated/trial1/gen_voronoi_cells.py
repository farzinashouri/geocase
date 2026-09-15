"""Compute Voronoi cells for a set of points, clipped to a bounding rectangle."""

from shapely import voronoi_polygons
from shapely.geometry import MultiPoint, Point, box


def voronoi_cells(points, bounds):
    """Return the Voronoi cell of each point, clipped to ``bounds``.

    points: list of N distinct (x, y) tuples.
    bounds: (minx, miny, maxx, maxy) rectangle containing all points.

    Returns a list of N Polygons where the i-th polygon is the region of
    ``bounds`` closer to points[i] than to any other input point.
    """
    if not points:
        return []

    minx, miny, maxx, maxy = bounds
    boundary = box(minx, miny, maxx, maxy)

    if len(points) == 1:
        return [boundary]

    diagram = voronoi_polygons(MultiPoint(points), extend_to=boundary)
    clipped = [cell.intersection(boundary) for cell in diagram.geoms]

    cells = [None] * len(points)
    unmatched = list(range(len(clipped)))
    for i, (x, y) in enumerate(points):
        p = Point(x, y)
        for j in unmatched:
            if clipped[j].covers(p):
                cells[i] = clipped[j]
                unmatched.remove(j)
                break

    return cells