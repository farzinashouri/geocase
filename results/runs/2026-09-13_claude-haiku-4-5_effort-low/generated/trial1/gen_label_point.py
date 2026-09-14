from shapely.geometry import Point, Polygon


def label_point(polygon: Polygon) -> Point:
    """
    Return a Point inside the polygon suitable for placing a text label.
    
    Tries to use the centroid if it's inside the polygon, otherwise
    returns a representative point guaranteed to be inside.
    """
    centroid = polygon.centroid
    if centroid.within(polygon):
        return centroid
    return polygon.representative_point()