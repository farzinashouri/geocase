def dedupe_geoms(geoms):
    """
    Remove duplicate geometries, keeping the first occurrence and preserving order.
    
    Two geometries are considered duplicates if they describe exactly the same
    set of points in the plane, regardless of coordinate sequence differences.
    
    Args:
        geoms: List of shapely geometries
        
    Returns:
        List with duplicate geometries removed
    """
    result = []
    for geom in geoms:
        if not any(geom.equals(seen_geom) for seen_geom in result):
            result.append(geom)
    return result