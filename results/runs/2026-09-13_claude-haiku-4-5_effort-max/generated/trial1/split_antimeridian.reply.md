```python
from shapely.geometry import Polygon

def split_antimeridian(polygon):
    """
    Split a polygon crossing the antimeridian into non-crossing polygons.
    
    Args:
        polygon: A shapely Polygon with lon/lat in EPSG:4326
    
    Returns:
        A list of Polygons that don't cross the antimeridian. If the input
        polygon doesn't cross the antimeridian, returns [polygon].
    """
    coords = list(polygon.exterior.coords)[:-1]
    
    crosses = any(abs(coords[i+1][0] - coords[i][0]) > 180 for i in range(len(coords)-1))
    if not crosses:
        return [polygon]
    
    def interpolate_crossing(lon1, lat1, lon2, lat2):
        """Find latitude at antimeridian crossing and which boundary crossed first."""
        lon_diff = lon2 - lon1
        if lon_diff > 180:
            t = (-180 - lon1) / (lon2 - lon1 - 360)
            lat_cross = lat1 + t * (lat2 - lat1)
            return lat_cross, False
        else:
            t = (180 - lon1) / (lon2 - lon1 + 360)
            lat_cross = lat1 + t * (lat2 - lat1)
            return lat_cross, True
    
    new_coords = []
    for i in range(len(coords)):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[(i+1) % len(coords)]
        
        new_coords.append((lon1, lat1))
        
        if abs(lon2 - lon1) > 180:
            lat_cross, is_180_first = interpolate_crossing(lon1, lat1, lon2, lat2)
            if is_180_first:
                new_coords.append((180, lat_cross))
                new_coords.append((-180, lat_cross))
            else:
                new_coords.append((-180, lat_cross))
                new_coords.append((180, lat_cross))
    
    east_coords = []
    west_coords = []
    
    for lon, lat in new_coords:
        if lon >= 0:
            east_coords.append((lon, lat))
        if lon <= 0:
            west_coords.append((lon, lat))
    
    polygons = []
    for coords_list in [east_coords, west_coords]:
        if len(coords_list) >= 3:
            coords_closed = coords_list + [coords_list[0]]
            try:
                p = Polygon(coords_closed)
                if p.is_valid and p.area > 0:
                    polygons.append(p)
            except:
                pass
    
    return polygons if polygons else [polygon]
```