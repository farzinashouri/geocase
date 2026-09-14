```python
import numpy as np
from shapely.geometry import Polygon, box
from scipy.spatial import Voronoi


def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells clipped to a rectangular bounds.
    
    Args:
        points: List of N (x, y) tuples in a projected coordinate system
        bounds: Tuple (minx, miny, maxx, maxy) containing all points
    
    Returns:
        List of N shapely Polygon objects representing Voronoi cells
    """
    points_array = np.array(points, dtype=float)
    minx, miny, maxx, maxy = bounds
    
    # Compute Voronoi diagram
    vor = Voronoi(points_array)
    
    # Create bounding polygon for clipping
    bounds_poly = box(minx, miny, maxx, maxy)
    
    # Create a large polygon to handle unbounded regions
    width = maxx - minx
    height = maxy - miny
    margin = max(width, height) * 10
    large_poly = box(minx - margin, miny - margin, maxx + margin, maxy + margin)
    
    cells = []
    
    for i in range(len(points_array)):
        # Get the region for this point
        region_idx = vor.point_region[i]
        region_vertices_indices = vor.regions[region_idx]
        
        if len(region_vertices_indices) == 0:
            cells.append(Polygon())
            continue
        
        # Extract finite vertices (ignore -1 which represents infinity)
        vertices = []
        has_infinite = False
        for v_idx in region_vertices_indices:
            if v_idx == -1:
                has_infinite = True
            else:
                vertices.append(vor.vertices[v_idx])
        
        if len(vertices) < 3:
            cells.append(Polygon())
            continue
        
        # Create polygon from vertices
        polygon = Polygon(vertices)
        
        # For unbounded regions, clip to the large polygon first
        if has_infinite:
            polygon = polygon.intersection(large_poly)
        
        # Clip to the actual bounds
        clipped = polygon.intersection(bounds_poly)
        cells.append(clipped)
    
    return cells
```