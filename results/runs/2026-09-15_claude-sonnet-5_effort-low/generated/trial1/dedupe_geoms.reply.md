```python
from shapely.geometry.base import BaseGeometry
from shapely import normalize


def dedupe_geoms(geoms: list[BaseGeometry]) -> list[BaseGeometry]:
    seen = set()
    result = []
    for geom in geoms:
        key = normalize(geom).wkb
        if key not in seen:
            seen.add(key)
            result.append(geom)
    return result
```