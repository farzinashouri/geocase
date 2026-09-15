```python
"""Compute the intersection of two 2D line segments."""

from shapely.geometry import LineString, Point


def segment_intersection(a, b):
    """Return None, a point, or a segment describing the shared portion of two segments.

    Args:
        a: Segment ((x1, y1), (x2, y2)).
        b: Segment ((x1, y1), (x2, y2)).

    Returns:
        None if the segments share no point, a tuple (x, y) if they share
        exactly one point, or a tuple of two endpoints ((xa, ya), (xb, yb))
        if they share more than one point.
    """
    line_a = LineString(a)
    line_b = LineString(b)

    inter = line_a.intersection(line_b)

    if inter.is_empty:
        return None

    if isinstance(inter, Point):
        return (inter.x, inter.y)

    coords = list(inter.coords)
    return (coords[0], coords[-1])
```