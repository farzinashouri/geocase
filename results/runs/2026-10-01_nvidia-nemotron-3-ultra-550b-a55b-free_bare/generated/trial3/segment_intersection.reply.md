```python
from shapely.geometry import LineString

def segment_intersection(a, b):
    """
    Compute the intersection of two 2D line segments.

    Parameters
    ----------
    a : ((float, float), (float, float))
        First segment as ((x1, y1), (x2, y2)).
    b : ((float, float), (float, float))
        Second segment as ((x1, y1), (x2, y2)).

    Returns
    -------
    None | tuple[float, float] | tuple[tuple[float, float], tuple[float, float]]
        - None if the segments do not intersect.
        - A point (x, y) if they intersect in exactly one point.
        - A segment ((xa, ya), (xb, yb)) giving the endpoints of the overlapping portion
          if they intersect in more than one point (i.e., they are collinear and overlap).
    """
    line_a = LineString(a)
    line_b = LineString(b)
    inter = line_a.intersection(line_b)

    if inter.is_empty:
        return None

    geom_type = inter.geom_type
    if geom_type == "Point":
        return (inter.x, inter.y)

    if geom_type == "LineString":
        coords = list(inter.coords)
        # The intersection of two segments is a single contiguous segment,
        # so the first and last coordinates are its endpoints.
        return (coords[0], coords[-1])

    # For two simple segments, other geometry types (MultiLineString, GeometryCollection)
    # should not occur. If they do, treat as no intersection.
    return None
```