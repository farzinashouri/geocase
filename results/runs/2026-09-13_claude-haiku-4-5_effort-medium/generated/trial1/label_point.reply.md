```python
from shapely.geometry import Point

def label_point(polygon):
    """
    Find a point inside a polygon suitable for placing a text label.
    
    Args:
        polygon: A shapely Polygon object in any coordinate system
        
    Returns:
        A shapely Point guaranteed to lie inside the polygon
    """
    # Try centroid first - it's usually the best
    centroid = polygon.centroid
    if polygon.contains(centroid):
        return centroid
    
    # Grid-based pole of inaccessibility for non-convex polygons
    minx, miny, maxx, maxy = polygon.bounds
    width, height = maxx - minx, maxy - miny
    
    if width == 0 or height == 0:
        return polygon.representative_point()
    
    cell_size = min(width, height) / 4
    best_point = None
    best_dist = -1
    
    for precision_iter in range(4):
        cell = cell_size / (2 ** precision_iter)
        x = minx + cell / 2
        while x < maxx:
            y = miny + cell / 2
            while y < maxy:
                p = Point(x, y)
                if polygon.contains(p):
                    d = p.distance(polygon.exterior)
                    if d > best_dist:
                        best_dist = d
                        best_point = p
                y += cell
            x += cell
    
    return best_point or polygon.representative_point()
```