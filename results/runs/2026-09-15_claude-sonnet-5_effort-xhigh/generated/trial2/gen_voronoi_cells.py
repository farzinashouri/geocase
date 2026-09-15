"""Compute the Voronoi diagram of a set of points, clipped to a rectangle."""

from shapely.geometry import MultiPoint, Point, box
from shapely.ops import voronoi_diagram


def voronoi_cells(points, bounds):
    if not points:
        return []

    minx, miny, maxx, maxy = bounds
    envelope = box(minx, miny, maxx, maxy)

    if len(points) == 1:
        return [envelope]

    diagram = voronoi_diagram(MultiPoint(list(points)), envelope=envelope)
    cells = [envelope.intersection(cell) for cell in diagram.geoms]

    # voronoi_diagram does not guarantee the output order matches the input
    # order, so match each cell back to its generating site: every site is
    # strictly closer to itself than to any other (distinct) site, so it
    # lies in (or, at worst, on the boundary of) exactly its own cell.
    ordered = [None] * len(points)
    remaining = list(range(len(cells)))
    for i, (x, y) in enumerate(points):
        site = Point(x, y)
        for j in remaining:
            if cells[j].intersects(site):
                ordered[i] = cells[j]
                remaining.remove(j)
                break

    return ordered