from shapely.geometry import Polygon, Point

def label_point(polygon):
    """
    Find a point inside the polygon suitable for label placement.
    
    Uses iterative grid search to locate the pole of inaccessibility
    (the point farthest from polygon edges).
    
    Args:
        polygon: A shapely Polygon object (any coordinate system)
        
    Returns:
        A shapely Point inside the polygon
    """
    bounds = polygon.bounds
    minx, miny, maxx, maxy = bounds
    width = maxx - minx
    height = maxy - miny
    
    # Grid cell size (1/4 of minimum polygon dimension)
    cell_size = min(width, height) / 4
    
    # Start with centroid if inside, else representative point
    if polygon.centroid.within(polygon):
        best_point = polygon.centroid
    else:
        best_point = polygon.representative_point()
    
    best_distance = polygon.exterior.distance(best_point)
    
    # Multi-level grid search for refinement
    for _ in range(3):
        y = miny
        while y < maxy:
            x = minx
            while x < maxx:
                candidate = Point(x, y)
                if polygon.contains(candidate):
                    dist = polygon.exterior.distance(candidate)
                    if dist > best_distance:
                        best_point = candidate
                        best_distance = dist
                x += cell_size
            y += cell_size
        cell_size = cell_size / 2
    
    return best_point