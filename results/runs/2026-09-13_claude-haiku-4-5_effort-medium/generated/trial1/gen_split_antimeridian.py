from shapely.geometry import Polygon


def split_antimeridian(polygon):
    """
    Split a polygon that crosses the antimeridian into separate valid polygons.
    
    Args:
        polygon: A shapely Polygon with coordinates in EPSG:4326 (lon/lat)
                with longitudes in [-180, 180].
    
    Returns:
        A list of Polygon objects that together cover the same region without
        crossing the antimeridian.
    """
    coords = list(polygon.exterior.coords)
    
    # Find antimeridian crossings
    crossings = []
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        dlon = lon2 - lon1
        
        if abs(dlon) > 180:
            # Interpolate to find crossing point
            if dlon < -180:  # Crossing from + to -
                t = (180 - lon1) / (dlon + 360)
                crossing_lon = 180
            else:  # Crossing from - to +
                t = (-180 - lon1) / (dlon - 360)
                crossing_lon = -180
            
            crossing_lat = lat1 + t * (lat2 - lat1)
            crossings.append((i, crossing_lon, crossing_lat))
    
    # If no crossing or unexpected number, return original polygon
    if len(crossings) != 2:
        return [polygon]
    
    # Sort crossings by position in the coordinate list
    (i1, lon1, lat1), (i2, lon2, lat2) = sorted(crossings)
    
    # Build western ring (from crossing 1 to crossing 2)
    ring_west = [(lon1, lat1)]
    for i in range(i1 + 1, i2 + 1):
        ring_west.append(coords[i])
    ring_west.append((lon2, lat2))
    ring_west.append((lon1, lat1))
    
    # Build eastern ring (from crossing 2 back to crossing 1)
    ring_east = [(lon2, lat2)]
    for i in range(i2 + 1, len(coords) - 1):
        ring_east.append(coords[i])
    for i in range(0, i1 + 1):
        ring_east.append(coords[i])
    ring_east.append((lon1, lat1))
    ring_east.append((lon2, lat2))
    
    # Normalize to ensure no crossing
    ring_west = [(-180 if lon == 180 else lon, lat) for lon, lat in ring_west]
    ring_east = [(180 if lon == -180 else lon, lat) for lon, lat in ring_east]
    
    # Create valid polygons
    polygons = []
    for ring in [ring_west, ring_east]:
        if len(ring) >= 4:
            try:
                p = Polygon(ring)
                if p.is_valid and p.area > 0:
                    polygons.append(p)
            except Exception:
                pass
    
    return polygons if polygons else [polygon]