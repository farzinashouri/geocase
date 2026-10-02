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
        For each point, the index of the polygon that contains it (boundary counts as contained).
        If a point lies on a boundary shared by several polygons, the smallest index is returned.
        If a point is not contained in any polygon, None is returned.
    """
    if not polygons:
        return [None] * len(points)

    # Build a spatial index for fast querying
    tree = STRtree(polygons)

    result = []
    for pt in points:
        point = Point(pt)
        # Find all polygons that cover the point (including boundary)
        candidate_indices = tree.query(point, predicate="covers")
        if candidate_indices.size == 0:
            result.append(None)
        else:
            # Return the smallest index among candidates
            result.append(int(candidate_indices.min()))
    return result
```