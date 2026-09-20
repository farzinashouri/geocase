def dedupe_geoms(geoms):
    """
    Remove duplicate geometries from a list, preserving order and first occurrence.
    
    Two geometries are considered duplicates if they describe the same
    set of points, even if their coordinate sequences differ.
    """
    result = []
    normalized_seen = []
    
    for geom in geoms:
        normalized = geom.normalize()
        
        is_duplicate = any(normalized.equals(seen) for seen in normalized_seen)
        
        if not is_duplicate:
            result.append(geom)
            normalized_seen.append(normalized)
    
    return result