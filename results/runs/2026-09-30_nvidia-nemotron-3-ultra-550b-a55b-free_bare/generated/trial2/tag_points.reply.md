```python
from shapely.geometry import Point
from shapely.strtree import STRtree

def tag_points(points, polygons):
    """
    Tags each point with the index of the polygon that contains it.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates.
    polygons : list[shapely.Polygon]
        List of shapely Polygon objects. Interiors do not overlap, but boundaries may be shared.

    Returns
    -------
    list[int | None]
        For each point, the index of the polygon that contains it (including boundary),
        or None if the point is not in any polygon. If a point lies on a shared boundary,
        the smallest index is returned.
    """
    if not polygons:
        return [None] * len(points)

    # Build spatial index for efficient querying
    tree = STRtree(polygons)

    result = []
    for x, y in points:
        pt = Point(x, y)
        # Find all polygons that cover the point (interior or boundary)
        candidate_indices = tree.query(pt, predicate="covers")
        if len(candidate_indices) == 0:
            result.append(None)
        else:
            # Return the smallest index among covering polygons
            result.append(int(min(candidate_indices)))
    return result
```