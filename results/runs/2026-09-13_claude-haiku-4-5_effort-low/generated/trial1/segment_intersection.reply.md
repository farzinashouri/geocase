```python
from shapely.geometry import LineString


def segment_intersection(a, b):
    line_a = LineString(a)
    line_b = LineString(b)
    intersection = line_a.intersection(line_b)
    
    if intersection.is_empty:
        return None
    if intersection.geom_type == 'Point':
        return (intersection.x, intersection.y)
    elif intersection.geom_type == 'LineString':
        coords = list(intersection.coords)
        return (coords[0], coords[-1])
    return None
```