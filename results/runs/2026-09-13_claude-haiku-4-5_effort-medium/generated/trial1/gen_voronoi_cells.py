from shapely.geometry import Polygon, box
from scipy.spatial import Voronoi
import numpy as np


def voronoi_cells(points, bounds):
    """Compute Voronoi cells clipped to bounds.
    
    Args:
        points: List of N distinct (x, y) tuples in projected coordinates
        bounds: Rectangle (minx, miny, maxx, maxy)
    
    Returns:
        List of N Shapely Polygon objects
    """
    points_array = np.array(points, dtype=float)
    minx, miny, maxx, maxy = bounds
    bounds_poly = box(minx, miny, maxx, maxy)
    
    vor = Voronoi(points_array)
    
    width = maxx - minx
    height = maxy - miny
    size = max(width, height) if max(width, height) > 0 else 1
    far = size * 1000
    large_box = box(minx - far, miny - far, maxx + far, maxy + far)
    
    cells = []
    for i in range(len(points_array)):
        region_idx = vor.point_region[i]
        region_vertex_indices = vor.regions[region_idx]
        
        valid_indices = [idx for idx in region_vertex_indices if idx >= 0]
        
        if len(valid_indices) >= 3:
            vertices = vor.vertices[valid_indices]
            region_poly = Polygon(vertices)
        else:
            region_poly = large_box
        
        cell = region_poly.intersection(bounds_poly)
        cells.append(cell)
    
    return cells