```python
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, box


def voronoi_cells(points, bounds):
    points_array = np.array(points)
    minx, miny, maxx, maxy = bounds
    bbox = box(minx, miny, maxx, maxy)
    
    vor = Voronoi(points_array)
    cells = []
    
    for i in range(len(points)):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        
        finite_indices = [idx for idx in region if idx != -1]
        
        if len(finite_indices) < 3:
            cells.append(bbox)
            continue
        
        vertices = vor.vertices[finite_indices]
        
        centroid = vertices.mean(axis=0)
        angles = np.arctan2(vertices[:, 1] - centroid[1], 
                           vertices[:, 0] - centroid[0])
        sorted_vertices = vertices[np.argsort(angles)]
        
        cell_polygon = Polygon(sorted_vertices)
        clipped_cell = cell_polygon.intersection(bbox)
        cells.append(clipped_cell)
    
    return cells
```