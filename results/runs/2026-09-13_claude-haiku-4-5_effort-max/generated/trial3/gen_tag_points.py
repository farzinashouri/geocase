from shapely.geometry import Point


def tag_points(points, polygons):
    """
    Tag each point with the index of the containing polygon.
    
    Points on boundaries count as contained. If a point lies on a boundary
    shared by multiple polygons, returns the smallest polygon index.
    
    Args:
        points: List of (x, y) tuples
        polygons: List of shapely Polygon objects
    
    Returns:
        List of polygon indices or None, one per input point in order
    """
    result = []
    
    for x, y in points:
        point = Point(x, y)
        containing_indices = []
        
        for i, polygon in enumerate(polygons):
            # Check if point is in polygon interior or on boundary
            if polygon.contains(point) or polygon.exterior.contains(point):
                containing_indices.append(i)
        
        if containing_indices:
            result.append(min(containing_indices))
        else:
            result.append(None)
    
    return result