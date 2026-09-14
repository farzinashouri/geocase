```python
from shapely.geometry import LineString

def segment_intersection(a, b):
    seg_a = LineString(a)
    seg_b = LineString(b)
    
    intersection = seg_a.intersection(seg_b)
    
    if intersection.is_empty:
        return None
    
    if intersection.geom_type == 'Point':
        x, y = intersection.x, intersection.y
        return (x, y)
    elif intersection.geom_type == 'LineString':
        coords = list(intersection.coords)
        return (coords[0], coords[-1])
    
    return None
```