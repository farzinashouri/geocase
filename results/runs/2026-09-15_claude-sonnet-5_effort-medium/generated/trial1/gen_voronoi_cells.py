"""Compute Voronoi cells clipped to a rectangular boundary."""

from shapely.geometry import Polygon, box
from shapely.ops import voronoi_diagram, unary_union
from shapely.geometry import MultiPoint


def voronoi_cells(points, bounds):
    minx, miny, maxx, maxy = bounds
    boundary = box(minx, miny, maxx, maxy)

    width = maxx - minx
    height = maxy - miny
    diag = (width ** 2 + height ** 2) ** 0.5
    envelope_size = max(diag * 4, 1.0)

    multipoint = MultiPoint(points)
    diagram = voronoi_diagram(multipoint, envelope=boundary.buffer(envelope_size))

    raw_cells = list(diagram.geoms)

    cells = []
    for pt in points:
        for cell in raw_cells:
            if cell.contains(pt) or cell.intersects(pt.__class__ if False else None):
                pass
        cells.append(None)

    from shapely.geometry import Point

    result = [None] * len(points)
    for cell in raw_cells:
        for i, pt in enumerate(points):
            if cell.intersects(Point(pt)) or cell.contains(Point(pt)):
                result[i] = cell.intersection(boundary)
                break

    return [
        r if r is not None else Polygon()
        for r in result
    ]