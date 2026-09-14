import numpy as np
from shapely.geometry import Polygon, box
from scipy.spatial import Voronoi


def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells clipped to a bounding rectangle.
    
    Args:
        points: List of N (x, y) tuples in planar coordinates
        bounds: (minx, miny, maxx, maxy) rectangle containing all points
    
    Returns:
        List of N shapely Polygons, where polygon i is the Voronoi cell
        for point i, clipped to the bounds rectangle
    """
    points_array = np.array(points, dtype=float)
    minx, miny, maxx, maxy = bounds
    bbox = box(minx, miny, maxx, maxy)
    
    vor = Voronoi(points_array)
    
    cells = []
    for i in range(len(points_array)):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        
        if -1 in region:
            # Unbounded region: extend finite vertices along unbounded edges
            vertices = [vor.vertices[j] for j in region if j != -1]
            
            if len(vertices) >= 2:
                point_i = vor.points[i]
                extended_verts = list(vertices)
                large_dist = max(maxx - minx, maxy - miny) * 10
                
                for ridge_points, ridge_verts in zip(vor.ridge_points, vor.ridge_vertices):
                    if i not in ridge_points or -1 not in ridge_verts:
                        continue
                    
                    finite_idx = ridge_verts[ridge_verts != -1][0]
                    finite_vert = vor.vertices[finite_idx]
                    other_idx = ridge_points[1] if ridge_points[0] == i else ridge_points[0]
                    other_point = vor.points[other_idx]
                    
                    diff = other_point - point_i
                    perp = np.array([-diff[1], diff[0]])
                    norm = np.linalg.norm(perp)
                    if norm > 0:
                        perp = perp / norm
                        extended_verts.append(finite_vert + large_dist * perp)
                        extended_verts.append(finite_vert - large_dist * perp)
                
                if len(extended_verts) >= 3:
                    verts_array = np.array(extended_verts)
                    centroid = np.mean(verts_array, axis=0)
                    angles = np.arctan2(verts_array[:, 1] - centroid[1],
                                       verts_array[:, 0] - centroid[0])
                    sorted_verts = verts_array[np.argsort(angles)]
                    cell_poly = Polygon(sorted_verts)
                else:
                    cell_poly = bbox
            else:
                cell_poly = bbox
        else:
            # Bounded region
            vertices = vor.vertices[region]
            if len(vertices) >= 3:
                cell_poly = Polygon(vertices)
            else:
                cell_poly = bbox
        
        cells.append(cell_poly.intersection(bbox))
    
    return cells