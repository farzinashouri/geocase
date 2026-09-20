from shapely.geometry import Point

def tag_points(points, polygons):
    result = []
    for x, y in points:
        point = Point(x, y)
        containing_indices = [i for i, poly in enumerate(polygons) 
                             if poly.contains(point) or point.touches(poly)]
        result.append(min(containing_indices) if containing_indices else None)
    return result