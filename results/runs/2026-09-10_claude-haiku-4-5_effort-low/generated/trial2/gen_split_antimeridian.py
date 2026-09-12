from shapely.geometry import Polygon


def split_antimeridian(polygon):
    """
    Split a polygon that crosses the antimeridian into valid polygons.
    
    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        A polygon with lon/lat coordinates in EPSG:4326, longitudes in [-180, 180]
    
    Returns
    -------
    list of shapely.geometry.Polygon
        List of polygons that do not cross the antimeridian. A polygon that does
        not cross the antimeridian is returned unchanged as a single-element list.
    """
    coords = list(polygon.exterior.coords)
    
    # Check for antimeridian crossing by detecting large longitude jumps
    has_crossing = any(abs(coords[i + 1][0] - coords[i][0]) > 180
                       for i in range(len(coords) - 1))
    
    if not has_crossing:
        return [polygon]
    
    # Insert points at antimeridian boundaries where crossings occur
    expanded_coords = []
    for i in range(len(coords) - 1):
        expanded_coords.append(coords[i])
        
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        lon_diff = lon2 - lon1
        if abs(lon_diff) > 180:
            # Interpolate the latitude where the crossing occurs
            if lon_diff > 0:  # Wraps through +180 to -180
                t = (180 - lon1) / (lon2 + 360 - lon1)
                lat_cross = lat1 + t * (lat2 - lat1)
                expanded_coords.append((180.0, lat_cross))
                expanded_coords.append((-180.0, lat_cross))
            else:  # Wraps through -180 to +180
                t = (-180 - lon1) / (lon2 - 360 - lon1)
                lat_cross = lat1 + t * (lat2 - lat1)
                expanded_coords.append((-180.0, lat_cross))
                expanded_coords.append((180.0, lat_cross))
    
    expanded_coords.append(coords[-1])  # Add closing coordinate
    
    # Split expanded coordinates into separate polygon rings at boundary markers
    polygons = []
    i = 0
    
    while i < len(expanded_coords):
        ring = []
        
        while i < len(expanded_coords):
            ring.append(expanded_coords[i])
            i += 1
            
            # Detect when we've reached a boundary marker pair
            if len(ring) >= 2:
                if (abs(ring[-2][0]) == 180 and
                    abs(ring[-1][0]) == 180 and
                    ring[-2][0] != ring[-1][0]):
                    break
        
        # Create a polygon from this ring
        if len(ring) >= 3:
            ring_closed = ring + [ring[0]]
            try:
                poly = Polygon(ring_closed)
                if poly.is_valid and poly.area > 0:
                    polygons.append(poly)
            except Exception:
                pass
    
    return polygons if polygons else [polygon]