```python
import numpy as np
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
from sklearn.neighbors import BallTree


def voronoi_cells(points, bounds):
    points_array = np.array(points)
    minx, miny, maxx, maxy = bounds
    
    # Determine adaptive grid resolution
    width = maxx - minx
    height = maxy - miny
    max_dim = max(width, height)
    
    if max_dim > 0:
        cells_per_unit = 100 / max_dim
    else:
        cells_per_unit = 1
    
    nx = max(2, int(width * cells_per_unit))
    ny = max(2, int(height * cells_per_unit))
    
    # Create grid edges
    x_edges = np.linspace(minx, maxx, nx + 1)
    y_edges = np.linspace(miny, maxy, ny + 1)
    
    # Create grid cell centers
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    xx, yy = np.meshgrid(x_centers, y_centers)
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])
    
    # Find nearest input point for each grid cell
    tree = BallTree(points_array)
    _, nearest_indices = tree.query(grid_points, k=1)
    nearest_indices = nearest_indices.ravel()
    
    # Build polygon for each input point
    result = []
    for point_idx in range(len(points_array)):
        # Find cells nearest to this point
        cell_mask = nearest_indices == point_idx
        
        if not np.any(cell_mask):
            result.append(Polygon())
            continue
        
        # Get cell indices
        cell_linear_indices = np.where(cell_mask)[0]
        
        # Convert linear indices to grid coordinates
        cell_rows = cell_linear_indices // nx
        cell_cols = cell_linear_indices % nx
        
        # Create boxes for cells
        boxes = []
        for row, col in zip(cell_rows, cell_cols):
            cell_box = box(
                x_edges[col], y_edges[row],
                x_edges[col + 1], y_edges[row + 1]
            )
            boxes.append(cell_box)
        
        # Union all boxes
        poly = unary_union(boxes)
        result.append(poly)
    
    return result
```