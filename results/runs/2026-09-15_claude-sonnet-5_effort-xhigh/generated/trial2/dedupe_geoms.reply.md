```python
from shapely import normalize, to_wkb
from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms: list[BaseGeometry]) -> list[BaseGeometry]:
    seen = set()
    deduped = []
    for geom in geoms:
        # normalize() puts rings in a canonical start point and winding
        # direction and sorts parts/collections, so geometries that trace
        # the same set of points map to identical WKB regardless of how
        # they were originally constructed.
        key = to_wkb(normalize(geom))
        if key not in seen:
            seen.add(key)
            deduped.append(geom)
    return deduped
```