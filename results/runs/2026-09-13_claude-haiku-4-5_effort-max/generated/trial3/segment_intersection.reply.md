```python
from shapely.geometry import LineString


def segment_intersection(a, b):
    """
    Find the intersection of two 2D line segments.
    
    Args:
        a: Line segment as ((x1, y1), (x2, y2))
        b: Line segment as ((x1, y1), (x2, y2))
    
    Returns:
        None if no intersection
        A point (x, y) if exactly one intersection point
        A segment ((xa, ya), (xb, yb)) if segments overlap
    """
    line_a = LineString(a)
    line_b = LineString(b)
    
    intersection = line_a.intersection(line_b)
    
    if intersection.is_empty:
        return None
    elif intersection.geom_type == 'Point':
        return tuple(intersection.coords[0])
    elif intersection.geom_type == 'LineString':
        coords = list(intersection.coords)
        return (tuple(coords[0]), tuple(coords[-1]))
    
    return None
```