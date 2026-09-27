```python
"""Tag planar points by the polygon that contains them.

Importing this module has no side effects.
"""

from shapely import Point, STRtree


def tag_points(points, polygons):
    """Return, for each point, the index of the containing polygon.

    ``points`` is a list of ``(x, y)`` tuples and ``polygons`` a list of
    shapely ``Polygon`` objects in the same planar coordinate system whose
    interiors do not overlap (they may share boundaries). For each point, in
    input order, return the index of the polygon that contains it, treating a
    point on a polygon's boundary as contained. If several polygons share the
    boundary a point lies on, the smallest such index is returned. Points in no
    polygon get ``None``.
    """
    pts = [Point(x, y) for (x, y) in points]

    if not polygons:
        return [None] * len(pts)

    tree = STRtree(polygons)
    results = [None] * len(pts)

    for i, pt in enumerate(pts):
        # Candidate polygons whose bounding boxes contain the point.
        candidates = tree.query(pt)
        best = None
        for j in candidates:
            # ``covers`` counts boundary points as contained.
            if polygons[j].covers(pt):
                if best is None or j < best:
                    best = j
        results[i] = int(best) if best is not None else None

    return results
```