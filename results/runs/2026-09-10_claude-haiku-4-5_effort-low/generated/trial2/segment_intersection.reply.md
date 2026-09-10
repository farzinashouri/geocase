```python
from shapely.geometry import LineString, Point


def segment_intersection(a, b):
    """Find the intersection of two 2D line segments.
    
    Args:
        a: Line segment as ((x1, y1), (x2, y2))
        b: Line segment as ((x1, y1), (x2, y2))
    
    Returns:
        None if no intersection, (x, y) if point intersection,
        ((xa, ya), (xb, yb)) if segment intersection.
    """
    line_a = LineString(a)
    line_b = LineString(b)
    
    intersection = line_a.intersection(line_b)
    
    if intersection.is_empty:
        return None
    
    if isinstance(intersection, Point):
        return (intersection.x, intersection.y)
    elif isinstance(intersection, LineString):
        coords = list(intersection.coords)
        return (tuple(coords[0]), tuple(coords[1]))
    
    return None
```