from shapely.geometry import Point, Polygon


def label_point(polygon: Polygon) -> Point:
    """
    Find a point inside a polygon suitable for text label placement.
    
    Args:
        polygon: A shapely Polygon in any coordinate system
        
    Returns:
        A shapely Point guaranteed to lie inside the polygon
    """
    centroid = polygon.centroid
    
    # Use centroid if it's inside the polygon
    if polygon.contains(centroid):
        return centroid
    
    # Fall back to representative_point for non-convex polygons
    return polygon.representative_point()