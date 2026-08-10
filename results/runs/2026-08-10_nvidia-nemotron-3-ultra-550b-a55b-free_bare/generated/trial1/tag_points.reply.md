```python
"""
Module for tagging points with containing polygon indices.

Provides a function `tag_points(points, polygons)` that returns, for each point,
the index of the polygon that contains it (including boundaries), or None if
the point is not contained in any polygon. If a point lies on a boundary shared
by multiple polygons, the smallest index is returned.
"""

from shapely.geometry import Point
from shapely.strtree import STRtree


def tag_points(points, polygons):
    """
    Tag each point with the index of the polygon that contains it.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinate tuples.
    polygons : list[shapely.Polygon]
        List of shapely Polygon objects. Polygons may share boundaries but their
        interiors do not overlap.

    Returns
    -------
    list[int | None]
        List of the same length as `points`. Each entry is the index of the
        polygon containing the corresponding point (boundary counts as contained),
        or None if the point is not in any polygon. If a point lies on a boundary
        shared by several polygons, the smallest index is returned.
    """
    if not polygons:
        return [None] * len(points)

    # Build spatial index for fast candidate lookup
    tree = STRtree(polygons)

    results = []
    for x, y in points:
        pt = Point(x, y)
        # Query returns indices of polygons whose bounding boxes intersect the point
        candidate_indices = tree.query(pt, predicate="intersects")
        # Ensure we check in increasing index order to satisfy "smallest index" rule
        for idx in sorted(candidate_indices):
            if polygons[idx].covers(pt):
                results.append(int(idx))
                break
        else:
            results.append(None)

    return results
```