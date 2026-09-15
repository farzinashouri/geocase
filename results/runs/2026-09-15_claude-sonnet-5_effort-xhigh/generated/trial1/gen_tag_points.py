"""Tag each point with the index of the polygon (if any) that contains it."""

from shapely.geometry import Point
from shapely.strtree import STRtree


def tag_points(points, polygons):
    if not polygons:
        return [None] * len(points)

    tree = STRtree(polygons)
    results = []
    for x, y in points:
        pt = Point(x, y)
        candidate_indices = sorted(int(i) for i in tree.query(pt))
        match = next(
            (i for i in candidate_indices if polygons[i].intersects(pt)), None
        )
        results.append(match)
    return results