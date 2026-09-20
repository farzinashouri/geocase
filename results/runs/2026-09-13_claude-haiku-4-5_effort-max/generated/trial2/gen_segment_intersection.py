from shapely.geometry import LineString

def segment_intersection(a, b):
    line_a = LineString(a)
    line_b = LineString(b)
    
    intersection = line_a.intersection(line_b)
    
    if intersection.is_empty:
        return None
    elif intersection.geom_type == 'Point':
        return tuple(intersection.coords[0])
    elif intersection.geom_type == 'LineString':
        coords = list(intersection.coords)
        return (tuple(coords[0]), tuple(coords[-1]))
    else:
        return None