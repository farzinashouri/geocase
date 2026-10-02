```python
"""Module for computing the intersection of two 2D line segments."""

def segment_intersection(a, b):
    """
    Compute the intersection of two line segments.

    Parameters
    ----------
    a : tuple[tuple[float, float], tuple[float, float]]
        First segment as ((x1, y1), (x2, y2)).
    b : tuple[tuple[float, float], tuple[float, float]]
        Second segment as ((x1, y1), (x2, y2)).

    Returns
    -------
    None or tuple[float, float] or tuple[tuple[float, float], tuple[float, float]]
        None if the segments have no point in common;
        a point (x, y) if they intersect in exactly one point;
        a segment ((xa, ya), (xb, yb)) giving the endpoints of the shared portion
        if they overlap in more than one point.
    """
    from shapely.geometry import LineString

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
        # The overlapping part of two straight segments is a straight segment,
        # so the LineString has at least two points (start and end).
        return (tuple(coords[0]), tuple(coords[-1]))
    else:
        # For two line segments this case should not occur (e.g., GeometryCollection),
        # but we return None for safety.
        return None
```