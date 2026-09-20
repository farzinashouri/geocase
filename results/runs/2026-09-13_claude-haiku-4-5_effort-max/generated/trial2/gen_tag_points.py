from shapely.geometry import Point


def tag_points(points, polygons):
    """
    Tag each point with the index of the polygon containing it.
    
    Args:
        points: List of (x, y) tuples
        polygons: List of shapely Polygon objects
        
    Returns:
        List with one entry per point: polygon index (0-based) or None
    """
    result = []
    for point in points:
        pt = Point(point)
        containing_indices = [i for i, poly in enumerate(polygons) if poly.contains(pt)]
        result.append(min(containing_indices) if containing_indices else None)
    return result