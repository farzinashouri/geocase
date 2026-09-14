```python
import numpy as np
from shapely.geometry import Point, Polygon


def label_point(polygon: Polygon) -> Point:
    centroid = polygon.centroid
    if polygon.contains(centroid):
        return centroid
    
    minx, miny, maxx, maxy = polygon.bounds
    width, height = maxx - minx, maxy - miny
    cell_size = max(width, height) / 12
    
    best_point = None
    best_distance = -1
    
    for xi in np.arange(minx, maxx, cell_size):
        for yi in np.arange(miny, maxy, cell_size):
            pt = Point(xi, yi)
            if polygon.contains(pt):
                dist = pt.distance(polygon.boundary)
                if dist > best_distance:
                    best_distance = dist
                    best_point = pt
    
    return best_point if best_point is not None else polygon.representative_point()
```