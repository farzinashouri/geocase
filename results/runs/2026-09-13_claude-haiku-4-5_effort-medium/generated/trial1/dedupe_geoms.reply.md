```python
def dedupe_geoms(geoms):
    """Remove duplicate geometries while preserving order and keeping first occurrence.
    
    Two geometries are considered duplicates if they describe the same set of points
    in the plane, even if their coordinate sequences differ.
    
    Args:
        geoms: A list of shapely geometry objects
        
    Returns:
        A new list with duplicate geometries removed, preserving order and 
        keeping the first occurrence of each unique geometry.
    """
    seen = []
    result = []
    
    for geom in geoms:
        normalized = geom.normalize()
        
        is_duplicate = any(normalized.equals(seen_norm) for seen_norm in seen)
        
        if not is_duplicate:
            result.append(geom)
            seen.append(normalized)
    
    return result
```