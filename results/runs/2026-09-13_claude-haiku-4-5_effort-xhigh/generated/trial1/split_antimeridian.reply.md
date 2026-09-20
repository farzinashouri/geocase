```python
from shapely.geometry import Polygon
import numpy as np

def split_antimeridian(polygon):
    """
    Split a polygon crossing the antimeridian into valid polygons.
    
    Takes a shapely Polygon with lon/lat coordinates in EPSG:4326 (lon in [-180, 180]).
    If the polygon crosses the antimeridian, returns a list of non-crossing polygons
    that together cover the same region. Otherwise returns the polygon unchanged
    in a single-element list.
    """
    coords = np.array(polygon.exterior.coords[:-1])
    
    lons = coords[:, 0]
    if np.max(lons) - np.min(lons) <= 180:
        return [polygon]
    
    coords_360 = coords.copy()
    coords_360[:, 0] = np.where(coords_360[:, 0] < 0, coords_360[:, 0] + 360, coords_360[:, 0])
    
    augmented = []
    for i in range(len(coords_360)):
        lon1, lat1 = coords_360[i]
        lon2, lat2 = coords_360[(i + 1) % len(coords_360)]
        
        augmented.append([lon1, lat1])
        
        if (lon1 < 180 < lon2) or (lon2 < 180 < lon1):
            t = (180 - lon1) / (lon2 - lon1)
            lat_cross = lat1 + t * (lat2 - lat1)
            augmented.append([180, lat_cross])
    
    augmented = np.array(augmented)
    
    eastern = augmented[augmented[:, 0] <= 180]
    western = augmented[augmented[:, 0] >= 180]
    western[:, 0] = np.where(western[:, 0] > 180, western[:, 0] - 360, western[:, 0])
    
    result = []
    if len(eastern) >= 3:
        result.append(Polygon(eastern))
    if len(western) >= 3:
        result.append(Polygon(western))
    
    return result if result else [polygon]
```