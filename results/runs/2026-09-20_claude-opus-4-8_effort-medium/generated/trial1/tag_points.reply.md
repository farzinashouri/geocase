```python
"""Assign each point to the polygon that contains it.

A point on a polygon boundary counts as contained. When a point lies on a
boundary shared by several polygons, the smallest polygon index wins.
"""

from shapely.geometry import Point
from shapely import STRtree


def tag_points(points, polygons):
    """Tag each point with the index of the polygon containing it.

    Args:
        points: list of (x, y) tuples in the same planar CRS as the polygons.
        polygons: list of shapely Polygons with non-overlapping interiors
            (they may share boundaries).

    Returns:
        A list with one entry per input point, in input order. Each entry is
        the index of the containing polygon (boundary counts as contained),
        or None if the point lies in no polygon. Ties on a shared boundary
        resolve to the smallest polygon index.
    """
    polygons = list(polygons)
    results = [None] * len(points)

    if not polygons:
        return results

    tree = STRtree(polygons)

    for i, xy in enumerate(points):
        pt = Point(xy)
        # Candidates whose bounding boxes intersect the point; these indices
        # refer back into the `polygons` list.
        candidates = tree.query(pt)
        best = None
        for j in candidates:
            j = int(j)
            # covers() treats boundary points as contained, unlike contains().
            if polygons[j].covers(pt):
                if best is None or j < best:
                    best = j
        results[i] = best

    return results
```