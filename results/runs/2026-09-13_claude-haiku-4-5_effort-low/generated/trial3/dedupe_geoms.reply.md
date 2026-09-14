```python
def dedupe_geoms(geoms):
    """Remove duplicate geometries from a list, keeping first occurrence.
    
    Geometries are considered duplicates if they represent the same set of points,
    regardless of coordinate sequence order or direction.
    """
    result = []
    for geom in geoms:
        if not any(geom.equals(existing) for existing in result):
            result.append(geom)
    return result
```