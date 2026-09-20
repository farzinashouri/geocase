```python
"""Tag each point with the index of the polygon that contains it."""

from shapely.geometry import Point


def tag_points(points, polygons):
    """Return, for each point, the index of the containing polygon or None.

    A point lying exactly on a polygon's boundary is considered contained.
    If several polygons contain a point (e.g. a shared boundary), the
    smallest polygon index is returned.
    """
    results = []
    for x, y in points:
        pt = Point(x, y)
        match = None
        for idx, polygon in enumerate(polygons):
            if polygon.covers(pt):
                match = idx
                break
        results.append(match)
    return results
```