from scipy.spatial import Voronoi
from shapely.geometry import Polygon, box
import numpy as np

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for points, clipped to a bounding rectangle.
    
    Args:
        points: List of N distinct (x, y) tuples in projected coordinates
        bounds: Tuple (minx, miny, maxx, maxy) containing all points
    
    Returns:
        List of N shapely Polygons representing Voronoi cells
    """
    points_array = np.array(points)
    minx, miny, maxx, maxy = bounds
    bounds_poly = box(minx, miny, maxx, maxy)
    
    vor = Voronoi(points_array)
    
    cells = []
    for i in range(len(points)):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        
        if -1 not in region:
            # Finite region
            vertices = vor.vertices[region]
            cell_poly = Polygon(vertices)
        else:
            # Infinite region - construct using finite vertices + bounds corners
            finite_mask = region >= 0
            finite_verts = vor.vertices[region[finite_mask]]
            
            # Include bounds corners to close infinite regions
            corners = np.array([
                [minx, miny],
                [maxx, miny],
                [maxx, maxy],
                [minx, maxy]
            ])
            
            all_verts = np.vstack([finite_verts, corners])
            cell_poly = Polygon(all_verts).convex_hull
        
        # Clip to bounds
        clipped = cell_poly.intersection(bounds_poly)
        cells.append(clipped)
    
    return cells