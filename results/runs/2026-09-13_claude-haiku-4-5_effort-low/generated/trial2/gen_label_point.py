from shapely.geometry import Point, Polygon


def label_point(polygon):
    """
    Find a suitable point inside the polygon for label placement.
    
    Returns the point inside the polygon that is furthest from its boundary,
    which is typically optimal for placing text labels.
    
    Args:
        polygon: A shapely Polygon object in any coordinate system
        
    Returns:
        A shapely Point inside the polygon
    """
    # Start with centroid if inside, else use representative_point
    if polygon.centroid.within(polygon):
        best_point = polygon.centroid
    else:
        best_point = polygon.representative_point()
    
    best_distance = best_point.distance(polygon.boundary)
    
    # Grid-based search for the point furthest from the boundary
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    cell_size = max(width, height) / 8
    
    if cell_size > 1e-10:  # Only search if polygon is large enough
        y = miny + cell_size / 2
        while y < maxy:
            x = minx + cell_size / 2
            while x < maxx:
                p = Point(x, y)
                if polygon.contains(p):
                    dist = p.distance(polygon.boundary)
                    if dist > best_distance:
                        best_distance = dist
                        best_point = p
                x += cell_size
            y += cell_size
    
    return best_point