from shapely.geometry import Polygon
import numpy as np

def split_antimeridian(polygon):
    """
    Split a polygon that crosses the antimeridian into valid polygons.
    
    Takes a shapely Polygon with EPSG:4326 coordinates where longitudes are in [-180, 180].
    If the polygon crosses the antimeridian, returns a list of polygons that together cover
    the same region and none of which crosses the antimeridian. Otherwise returns the polygon
    unchanged as a single-element list.
    
    Args:
        polygon: shapely.Polygon with exterior coordinates in EPSG:4326
        
    Returns:
        list of shapely.Polygon objects
    """
    
    coords = np.array(polygon.exterior.coords)
    lons = coords[:, 0]
    lats = coords[:, 1]
    
    # Check if polygon crosses the antimeridian
    # If max_lon - min_lon <= 180, it doesn't cross
    if np.max(lons) - np.min(lons) <= 180:
        return [polygon]
    
    # Insert intersection points at the antimeridian boundary
    new_coords = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = lons[i], lats[i]
        lon2, lat2 = lons[i + 1], lats[i + 1]
        
        new_coords.append([lon1, lat1])
        
        diff = lon2 - lon1
        if abs(diff) > 180:
            # Antimeridian crossing detected
            if diff > 0:  # Crossing from negative to positive longitude
                t1 = (-180 - lon1) / diff
                t2 = (180 - lon1) / diff
                lat_at_minus180 = lat1 + t1 * (lat2 - lat1)
                lat_at_180 = lat1 + t2 * (lat2 - lat1)
                new_coords.append([-180.0, lat_at_minus180])
                new_coords.append([180.0, lat_at_180])
            else:  # Crossing from positive to negative longitude
                t1 = (180 - lon1) / diff
                t2 = (-180 - lon1) / diff
                lat_at_180 = lat1 + t1 * (lat2 - lat1)
                lat_at_minus180 = lat1 + t2 * (lat2 - lat1)
                new_coords.append([180.0, lat_at_180])
                new_coords.append([-180.0, lat_at_minus180])
    
    new_coords.append(coords[-1])
    
    # Find indices of points on the antimeridian boundary
    am_indices = []
    for i, (lon, lat) in enumerate(new_coords):
        if abs(abs(lon) - 180.0) < 1e-10:
            am_indices.append(i)
    
    if not am_indices:
        return [polygon]
    
    # Build polygons from segments between consecutive boundary points
    polygons = []
    for k in range(len(am_indices)):
        start_idx = am_indices[k]
        end_idx = am_indices[(k + 1) % len(am_indices)]
        
        if start_idx < end_idx:
            segment = new_coords[start_idx:end_idx+1]
        else:
            # Wrap around
            segment = new_coords[start_idx:] + new_coords[:end_idx+1]
        
        if len(segment) >= 3:
            try:
                poly = Polygon(segment)
                if poly.is_valid and poly.area > 0:
                    polygons.append(poly)
            except:
                pass
    
    return polygons if polygons else [polygon]