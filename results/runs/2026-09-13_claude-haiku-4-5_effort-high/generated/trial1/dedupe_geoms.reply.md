```python
def dedupe_geoms(geoms):
    result = []
    for geom in geoms:
        if not any(geom.equals(existing) for existing in result):
            result.append(geom)
    return result
```