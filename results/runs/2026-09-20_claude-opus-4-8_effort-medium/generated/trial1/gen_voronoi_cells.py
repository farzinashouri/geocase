"""Compute Voronoi cells clipped to a bounding rectangle.

Given N distinct planar points inside a rectangle, produce for each point the
region of the rectangle whose locations are nearer to that point than to any
other input point. Importing this module has no side effects.
"""

from shapely import voronoi_polygons
from shapely.geometry import MultiPoint, Point, box


def voronoi_cells(points, bounds):
    """Return one shapely Polygon per input point.

    Args:
        points: list of N distinct (x, y) tuples in a planar coordinate system.
        bounds: rectangle (minx, miny, maxx, maxy) containing all the points.

    Returns:
        A list of N shapely Polygons. The i-th polygon is exactly the part of
        the ``bounds`` rectangle consisting of locations closer to
        ``points[i]`` than to any other input point.
    """
    minx, miny, maxx, maxy = bounds
    clip = box(minx, miny, maxx, maxy)

    pts = [Point(x, y) for (x, y) in points]

    # A single point owns the whole rectangle.
    if len(pts) == 1:
        return [clip]

    mp = MultiPoint(pts)

    # Extend the raw diagram to (at least) the clipping rectangle so that no
    # cell is truncated before we intersect with the exact rectangle. The
    # returned polygons are not guaranteed to be in input order, so we match
    # each cell back to its generating point by containment.
    diagram = voronoi_polygons(mp, extend_to=clip)
    cells = list(diagram.geoms)

    result = [None] * len(pts)
    unmatched = list(range(len(cells)))

    for i, p in enumerate(pts):
        found = None
        for j in unmatched:
            if cells[j].covers(p):
                found = j
                break
        if found is None:
            # Fallback: pick the cell whose interior is nearest to the point.
            found = min(unmatched, key=lambda j: cells[j].distance(p))
        unmatched.remove(found)
        result[i] = clip.intersection(cells[found])

    return result