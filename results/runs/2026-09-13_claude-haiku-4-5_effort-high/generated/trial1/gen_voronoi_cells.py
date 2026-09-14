from shapely.geometry import box, Polygon
import numpy as np


def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for points within a bounding rectangle.
    
    Parameters
    ----------
    points : list of (x, y) tuples
        N distinct points in a projected coordinate system
    bounds : (minx, miny, maxx, maxy)
        Rectangle containing all points
    
    Returns
    -------
    list of shapely.Polygon
        Voronoi cell for each input point
    """
    minx, miny, maxx, maxy = bounds
    points_array = np.array(points, dtype=np.float64)
    n = len(points_array)
    
    cells = []
    domain_size = max(maxx - minx, maxy - miny)
    
    for i in range(n):
        pi = points_array[i]
        cell = box(minx, miny, maxx, maxy)
        
        for j in range(n):
            if i == j:
                continue
            
            pj = points_array[j]
            mid = (pi + pj) * 0.5
            direction = pj - pi
            
            perp = np.array([-direction[1], direction[0]], dtype=np.float64)
            perp_norm = np.sqrt(perp[0]*perp[0] + perp[1]*perp[1])
            if perp_norm > 1e-10:
                perp = perp / perp_norm
            
            scale = domain_size * 2
            
            coords = [
                tuple(mid - direction * scale - perp * scale),
                tuple(mid - direction * scale + perp * scale),
                tuple(mid - direction * scale * 0.1 + perp * scale),
                tuple(mid - direction * scale * 0.1 - perp * scale),
            ]
            
            halfplane = Polygon(coords)
            cell = cell.intersection(halfplane)
        
        cells.append(cell)
    
    return cells