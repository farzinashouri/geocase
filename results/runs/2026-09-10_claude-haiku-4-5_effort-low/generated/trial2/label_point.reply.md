```python
from shapely.geometry import Polygon, Point

def label_point(polygon):
    """
    Find a point inside the polygon suitable for label placement.
    
    Prefers centroid if inside. Otherwise finds the point furthest from
    polygon boundaries using adaptive grid search.
    """
    # Centroid is ideal if it's inside the polygon
    centroid = polygon.centroid
    if polygon.contains(centroid):
        return centroid
    
    # Search for interior point furthest from edges
    minx, miny, maxx, maxy = polygon.bounds
    cell_size = max(maxx - minx, maxy - miny) / 12
    
    best_point = None
    best_distance = -1
    
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            candidate = Point(x, y)
            if polygon.contains(candidate):
                distance = polygon.exterior.distance(candidate)
                if distance > best_distance:
                    best_distance = distance
                    best_point = candidate
            y += cell_size
        x += cell_size
    
    # Fallback to guaranteed-inside point
    return best_point if best_point is not None else polygon.representative_point()
```