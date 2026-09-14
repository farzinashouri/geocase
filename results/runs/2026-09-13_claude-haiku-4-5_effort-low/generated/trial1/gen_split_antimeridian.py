from shapely.geometry import Polygon


def split_antimeridian(polygon):
    """
    Split a polygon that crosses the antimeridian into separate valid polygons.
    
    Args:
        polygon: A shapely Polygon in EPSG:4326 (lon/lat) with coordinates in [-180, 180]
    
    Returns:
        A list of shapely Polygons that together cover the same region without
        crossing the antimeridian (except at edges)
    """
    exterior = list(polygon.exterior.coords)
    n = len(exterior) - 1
    
    has_crossing = any(abs(exterior[i+1][0] - exterior[i][0]) > 180 for i in range(n))
    if not has_crossing:
        return [polygon]
    
    east = []
    west = []
    
    for i in range(n):
        lon1, lat1 = exterior[i][:2]
        lon2, lat2 = exterior[i + 1][:2]
        
        if lon1 > 0:
            east.append((lon1, lat1))
        elif lon1 < 0:
            west.append((lon1, lat1))
        else:
            east.append((lon1, lat1))
            west.append((lon1, lat1))
        
        lon_diff = lon2 - lon1
        if abs(lon_diff) <= 180:
            continue
        
        if lon_diff > 180:
            lon2_adj = lon2 - 360
            crossing_lon = -180
        else:
            lon2_adj = lon2 + 360
            crossing_lon = 180
        
        t = (crossing_lon - lon1) / (lon2_adj - lon1)
        lat_c = lat1 + t * (lat2 - lat1)
        
        if crossing_lon > 0:
            east.append((crossing_lon, lat_c))
            west.append((-crossing_lon, lat_c))
        else:
            east.append((-crossing_lon, lat_c))
            west.append((crossing_lon, lat_c))
    
    for ring in [east, west]:
        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])
    
    result = []
    for ring in [east, west]:
        if len(ring) >= 4:
            try:
                p = Polygon(ring)
                if p.is_valid and not p.is_empty:
                    result.append(p)
            except:
                pass
    
    return result if result else [polygon]