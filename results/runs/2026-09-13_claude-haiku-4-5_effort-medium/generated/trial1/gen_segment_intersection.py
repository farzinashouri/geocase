from shapely.geometry import LineString


def segment_intersection(a, b):
    """
    Find the intersection of two 2D line segments.
    
    Args:
        a: Segment as ((x1, y1), (x2, y2))
        b: Segment as ((x1, y1), (x2, y2))
    
    Returns:
        None if segments have no point in common
        (x, y) if segments have exactly one point in common
        ((xa, ya), (xb, yb)) if segments overlap
    """
    line_a = LineString(a)
    line_b = LineString(b)
    intersection = line_a.intersection(line_b)
    
    if intersection.is_empty:
        return None
    
    if intersection.geom_type == 'Point':
        return (intersection.x, intersection.y)
    elif intersection.geom_type == 'LineString':
        coords = list(intersection.coords)
        return (coords[0], coords[-1])
    
    return None