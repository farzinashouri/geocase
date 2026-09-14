from shapely.geometry import Polygon


def split_antimeridian(polygon):
    """
    Split a polygon crossing the antimeridian into non-crossing polygons.
    
    Takes a shapely Polygon with EPSG:4326 coordinates (lon/lat in [-180, 180]).
    Returns a list of valid Polygons that together cover the same region, with
    none crossing the antimeridian except at its edge.
    """
    coords = list(polygon.exterior.coords[:-1])
    n = len(coords)
    
    # Detect edges that cross the antimeridian (lon jump > 180°)
    crossing_edges = []
    for i in range(n):
        lon_diff = coords[(i + 1) % n][0] - coords[i][0]
        if abs(lon_diff) > 180:
            crossing_edges.append(i)
    
    if not crossing_edges:
        return [polygon]
    
    # Normalize longitudes to be continuous (add/subtract 360 as needed)
    lons = [c[0] for c in coords]
    norm_lons = [lons[0]]
    for i in range(1, n):
        delta = lons[i] - norm_lons[-1]
        if delta < -180:
            norm_lons.append(lons[i] + 360)
        elif delta > 180:
            norm_lons.append(lons[i] - 360)
        else:
            norm_lons.append(lons[i])
    
    # Split meridian at 180
    split_lon = 180
    
    # Insert crossing points at the antimeridian
    coords_with_crossings = []
    for i in range(n):
        lon, lat = coords[i]
        norm_lon = norm_lons[i]
        
        coords_with_crossings.append((lon, lat, norm_lon))
        
        if i in crossing_edges:
            # Interpolate the crossing point latitude
            lon_next, lat_next = coords[(i + 1) % n]
            norm_lon_next = norm_lons[(i + 1) % n]
            
            t = (split_lon - norm_lon) / (norm_lon_next - norm_lon)
            lat_cross = lat + t * (lat_next - lat)
            
            coords_with_crossings.append((split_lon, lat_cross, split_lon))
    
    # Separate coordinates into two rings based on split meridian
    rings = [[], []]
    for lon, lat, norm_lon in coords_with_crossings:
        ring_idx = 0 if norm_lon <= split_lon else 1
        
        # Denormalize: convert back to [-180, 180]
        out_lon = lon
        if norm_lon > 180:
            out_lon = lon - 360
        elif norm_lon < -180:
            out_lon = lon + 360
        
        rings[ring_idx].append((out_lon, lat))
    
    # Create polygons from rings
    polygons = []
    for ring in rings:
        if len(ring) >= 4:  # Need at least 3 unique points
            ring_closed = ring + [ring[0]]
            poly = Polygon(ring_closed)
            if poly.is_valid and poly.area > 0:
                polygons.append(poly)
    
    return polygons if polygons else [polygon]