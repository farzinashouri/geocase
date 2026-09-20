```python
from shapely.geometry import Polygon
import numpy as np


def split_antimeridian(polygon):
    """
    Split a polygon that crosses the antimeridian into non-crossing polygons.
    
    Args:
        polygon: A shapely Polygon with coordinates in EPSG:4326
                (longitude/latitude, lon in [-180, 180])
    
    Returns:
        A list of shapely Polygon objects that don't cross the antimeridian.
        If the input doesn't cross, returns [polygon] unchanged.
    """
    # Extract exterior ring coordinates (excluding the closing duplicate)
    ext_coords = np.array(polygon.exterior.coords[:-1])
    
    if len(ext_coords) < 3:
        return [polygon]
    
    # Detect antimeridian crossings by finding edges with large longitude jumps
    lon_diffs = np.diff(ext_coords[:, 0])
    crossing_indices = np.where(np.abs(lon_diffs) > 180)[0]
    
    if len(crossing_indices) == 0:
        return [polygon]
    
    # Insert points at the antimeridian crossing locations
    mod_coords = []
    for i in range(len(ext_coords)):
        mod_coords.append(ext_coords[i].tolist())
        
        if i in crossing_indices:
            # Interpolate crossing point at ±180
            p1 = ext_coords[i]
            p2 = ext_coords[(i + 1) % len(ext_coords)]
            
            lon_diff = p2[0] - p1[0]
            
            # Determine which boundary the crossing reaches
            if lon_diff > 180:
                cross_lon = 180.0
            else:  # lon_diff < -180
                cross_lon = -180.0
            
            # Linear interpolation for latitude
            t = (cross_lon - p1[0]) / lon_diff
            cross_lat = p1[1] + t * (p2[1] - p1[1])
            mod_coords.append([cross_lon, cross_lat])
    
    mod_coords = np.array(mod_coords)
    
    # Find all antimeridian boundary points
    boundary_indices = []
    for i, coord in enumerate(mod_coords):
        if abs(coord[0]) == 180:
            boundary_indices.append(i)
    
    if len(boundary_indices) < 2:
        return [polygon]
    
    # Create polygons from segments between consecutive boundary points
    result = []
    
    for k in range(len(boundary_indices)):
        start_idx = boundary_indices[k]
        end_idx = boundary_indices[(k + 1) % len(boundary_indices)]
        
        # Extract segment coordinates
        if start_idx <= end_idx:
            segment = mod_coords[start_idx:end_idx+1].tolist()
        else:
            # Wrap-around case
            segment = np.vstack([
                mod_coords[start_idx:],
                mod_coords[:end_idx+1]
            ]).tolist()
        
        # Create polygon if segment has enough points
        if len(segment) >= 3:
            segment.append(segment[0])  # Close the ring
            poly = Polygon(segment)
            
            if poly.is_valid and poly.area > 0:
                result.append(poly)
    
    return result if result else [polygon]
```