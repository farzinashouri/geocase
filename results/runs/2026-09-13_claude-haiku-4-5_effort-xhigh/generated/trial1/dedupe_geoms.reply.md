```python
def dedupe_geoms(geoms):
    """Remove duplicate geometries from a list, keeping the first occurrence.
    
    Two geometries are duplicates if they describe the same set of points,
    even if their coordinate sequences differ.
    """
    result = []
    for geom in geoms:
        if not any(geom.equals(existing) for existing in result):
            result.append(geom)
    return result
```