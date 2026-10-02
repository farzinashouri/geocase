```python
from shapely.geometry import Point
from shapely.strtree import STRtree

def tag_points(points, polygons):
    """
    Tag each point with the index of the polygon that contains it.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates.
    polygons : list[shapely.Polygon]
        List of polygons. Their interiors do not overlap, but they may share boundaries.

    Returns
    -------
    list[int | None]
        For each point, the index of the polygon that contains it (boundary counts as contained).
        If a point lies on a boundary shared by several polygons, the smallest index is returned.
        If a point is not contained in any polygon, None is returned.
    """
    if not polygons:
        return [None] * len(points)

    # Build a spatial index for fast candidate lookup
    tree = STRtree(polygons)

    results = []
    for pt in points:
        point = Point(pt)
        # Get indices of polygons whose bounding boxes intersect the point
        candidate_indices = tree.query(point)
        # Among candidates, find those that actually cover the point (including boundary)
        containing = [idx for idx in candidate_indices if polygons[idx].covers(point)]
        if containing:
            results.append(min(containing))
        else:
            results.append(None)
    return results
```