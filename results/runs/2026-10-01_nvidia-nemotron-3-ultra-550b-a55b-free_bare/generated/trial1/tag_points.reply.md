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
        List of polygons. Interiors do not overlap, but boundaries may be shared.

    Returns
    -------
    list[int | None]
        For each point, the index of the containing polygon (boundary counts as contained).
        If a point lies on a boundary shared by multiple polygons, the smallest index is returned.
        If no polygon contains the point, None is returned.
    """
    if not polygons:
        return [None] * len(points)

    # Build spatial index for polygons
    tree = STRtree(polygons)

    results = []
    for x, y in points:
        pt = Point(x, y)
        # Query returns indices of polygons whose bounding boxes intersect the point
        candidate_indices = tree.query(pt)
        containing = []
        for idx in candidate_indices:
            if polygons[idx].covers(pt):
                containing.append(idx)
        if containing:
            results.append(min(containing))
        else:
            results.append(None)
    return results
```