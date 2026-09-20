```python
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, box


def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells clipped to a rectangular boundary.
    
    Args:
        points: List of N (x, y) tuples in projected coordinates
        bounds: Tuple (minx, miny, maxx, maxy) defining the clipping rectangle
    
    Returns:
        List of N shapely Polygon objects representing clipped Voronoi cells
    """
    points = np.asarray(points, dtype=float)
    minx, miny, maxx, maxy = bounds
    
    vor = Voronoi(points)
    boundary = box(minx, miny, maxx, maxy)
    
    cells = []
    max_dim = max(maxx - minx, maxy - miny)
    
    for i in range(len(points)):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        
        if len(region) == 0 or all(v == -1 for v in region):
            cells.append(boundary)
            continue
        
        finite_verts = vor.vertices[[v for v in region if v != -1]]
        
        if len(finite_verts) < 3:
            cells.append(boundary)
            continue
        
        if -1 not in region:
            poly = Polygon(finite_verts)
        else:
            center = finite_verts.mean(axis=0)
            angles = np.arctan2(finite_verts[:, 1] - center[1],
                              finite_verts[:, 0] - center[0])
            finite_verts = finite_verts[np.argsort(angles)]
            
            extended_verts = []
            for j in range(len(finite_verts)):
                v = finite_verts[j]
                extended_verts.append(v)
                v_next = finite_verts[(j + 1) % len(finite_verts)]
                direction = v_next - v
                dist = np.linalg.norm(direction)
                if dist > 1e-10:
                    direction = direction / dist
                    extended_verts.append(v_next + direction * (10 * max_dim))
            
            poly = Polygon(extended_verts)
        
        clipped = poly.intersection(boundary)
        cells.append(clipped)
    
    return cells
```