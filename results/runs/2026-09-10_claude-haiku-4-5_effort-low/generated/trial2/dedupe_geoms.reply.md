```python
def dedupe_geoms(geoms):
    """
    Remove duplicate geometries from a list, preserving order.
    
    Two geometries are considered duplicates if they describe the same
    set of points in the plane, even if coordinate sequences differ.
    Preserves the first occurrence of each unique geometry.
    
    Args:
        geoms: List of shapely geometries
        
    Returns:
        List of geometries with duplicates removed, in original order
    """
    seen = set()
    result = []
    for geom in geoms:
        wkt = geom.normalize().wkt
        if wkt not in seen:
            seen.add(wkt)
            result.append(geom)
    return result
```