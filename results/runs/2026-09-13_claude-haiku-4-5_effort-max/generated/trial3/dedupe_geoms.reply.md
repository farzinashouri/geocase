```python
def dedupe_geoms(geoms):
    """
    Remove duplicate geometries from a list, keeping the first occurrence.
    
    Two geometries are considered duplicates if they describe the same set of
    points in the plane, regardless of coordinate ordering or ring direction.
    Order is preserved.
    
    Args:
        geoms: List of shapely geometries
        
    Returns:
        List of geometries with duplicates removed
    """
    result = []
    for geom in geoms:
        if not any(geom.equals(existing) for existing in result):
            result.append(geom)
    return result
```