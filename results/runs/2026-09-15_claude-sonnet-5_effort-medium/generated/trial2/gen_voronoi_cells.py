"""Voronoi diagram of points, clipped to a rectangular boundary."""

from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import voronoi_diagram


def voronoi_cells(points, bounds):
    """Compute the Voronoi cell of each point, clipped to bounds.

    Args:
        points: list of N distinct (x, y) tuples in a planar CRS.
        bounds: (minx, miny, maxx, maxy) rectangle containing all points.

    Returns:
        A list of N shapely Polygons, where the i-th polygon is the
        region of the rectangle closer to points[i] than to any other
        input point.
    """
    minx, miny, maxx, maxy = bounds
    rect = box(minx, miny, maxx, maxy)

    if len(points) == 1:
        return [rect]

    multipoint = MultiPoint(list(points))
    diagram = voronoi_diagram(multipoint, envelope=rect)
    raw_cells = list(diagram.geoms)

    cells = []
    for x, y in points:
        pt = Point(x, y)
        match = None
        for cell in raw_cells:
            if cell.intersects(pt):
                match = cell
                break
        if match is None:
            # Fall back to nearest cell in case of floating point issues
            match = min(raw_cells, key=lambda c: c.distance(pt))
        clipped = match.intersection(rect)
        cells.append(clipped)

    return cells