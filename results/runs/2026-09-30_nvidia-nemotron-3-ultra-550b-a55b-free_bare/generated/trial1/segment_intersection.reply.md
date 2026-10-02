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
    None or tuple or tuple of tuples
        - None if no intersection.
        - (x, y) if intersection is a single point.
        - ((xa, ya), (xb, yb)) if intersection is a segment (two endpoints).
    """
    line_a = LineString(a)
    line_b = LineString(b)
    inter = line_a.intersection(line_b)

    if inter.is_empty:
        return None

    geom_type = inter.geom_type
    if geom_type == 'Point':
        return (inter.x, inter.y)
    elif geom_type == 'LineString':
        coords = list(inter.coords)
        # A LineString from segment intersection always has at least two points.
        # Return the endpoints of the shared portion.
        return (coords[0], coords[-1])
    else:
        # For two straight segments, other geometry types (MultiLineString, GeometryCollection)
        # should not occur. Return None as a safe fallback.
        return None
```