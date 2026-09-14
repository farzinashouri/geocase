```python
import numpy as np
from shapely.geometry import Polygon, box


def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells clipped to a bounding rectangle.
    
    Args:
        points: List of N (x, y) tuples in projected coordinates
        bounds: Rectangle (minx, miny, maxx, maxy) containing all points
    
    Returns:
        List of N shapely Polygons representing Voronoi cells clipped to bounds
    """
    points_array = np.array(points, dtype=float)
    minx, miny, maxx, maxy = bounds
    bounds_width = maxx - minx
    bounds_height = maxy - miny
    scale = max(bounds_width, bounds_height) * 3
    
    cells = []
    for i in range(len(points_array)):
        cell = box(minx, miny, maxx, maxy)
        
        for j in range(len(points_array)):
            if i == j:
                continue
            
            pi, pj = points_array[i], points_array[j]
            mid = (pi + pj) / 2
            delta = pj - pi
            
            delta_len = np.sqrt(delta[0]**2 + delta[1]**2)
            delta_unit = delta / delta_len
            
            perp_unit = np.array([-delta_unit[1], delta_unit[0]])
            
            p1 = mid - scale * delta_unit + scale * perp_unit
            p2 = mid - scale * delta_unit - scale * perp_unit
            p3 = mid + scale * delta_unit - scale * perp_unit
            p4 = mid + scale * delta_unit + scale * perp_unit
            
            half_plane = Polygon([p1, p2, p3, p4])
            cell = cell.intersection(half_plane)
            
            if cell.is_empty:
                break
        
        if cell.geom_type == 'Polygon':
            cells.append(cell)
        else:
            cells.append(Polygon())
    
    return cells
```