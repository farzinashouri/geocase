import numpy as np
from shapely.geometry import Point


def label_point(polygon):
    """Return a point inside polygon suitable for label placement."""
    bounds = polygon.bounds
    minx, miny, maxx, maxy = bounds
    
    if maxx == minx or maxy == miny:
        return polygon.representative_point()
    
    xs = np.linspace(minx, maxx, 10)
    ys = np.linspace(miny, maxy, 10)
    
    best = polygon.representative_point()
    best_dist = -1
    
    for x in xs:
        for y in ys:
            p = Point(x, y)
            if polygon.contains(p):
                dist = p.distance(polygon.exterior)
                if dist > best_dist:
                    best_dist = dist
                    best = p
    
    return best