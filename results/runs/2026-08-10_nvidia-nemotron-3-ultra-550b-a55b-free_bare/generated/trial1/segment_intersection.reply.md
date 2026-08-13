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
        - A segment ((xa, ya), (xb, yb)) giving the endpoints of the shared portion
          if they overlap in more than one point.
    """
    line1 = LineString(a)
    line2 = LineString(b)
    inter = line1.intersection(line2)

    if inter.is_empty:
        return None

    geom_type = inter.geom_type
    if geom_type == 'Point':
        return (inter.x, inter.y)
    elif geom_type == 'LineString':
        coords = list(inter.coords)
        # The intersection of two segments is a single contiguous segment,
        # so its LineString representation has exactly two endpoints.
        return (tuple(coords[0]), tuple(coords[1]))
    else:
        # This case should not occur for two simple line segments,
        # but we handle it defensively.
        return None
```