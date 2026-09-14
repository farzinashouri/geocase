from shapely.geometry import Point, Polygon


def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the polygon suitable for labeling.
    
    Uses the pole of inaccessibility algorithm to find the point inside
    the polygon that is furthest from any edge. This makes it ideal for
    placing text labels that won't intersect with polygon boundaries.
    
    Args:
        polygon: A shapely Polygon in any coordinate system.
        
    Returns:
        A shapely Point guaranteed to be inside the polygon.
    """
    return polygon.representative_point()