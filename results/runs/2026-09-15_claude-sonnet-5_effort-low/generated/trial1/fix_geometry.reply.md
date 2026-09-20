```python
"""Repair invalid shapely Polygon/MultiPolygon geometries."""

from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid


def fix_geometry(geom):
    if geom.is_valid:
        return geom

    fixed = make_valid(geom)

    polys = []

    def collect(g):
        if g is None or g.is_empty:
            return
        if isinstance(g, Polygon):
            polys.append(g)
        elif hasattr(g, "geoms"):
            for sub in g.geoms:
                collect(sub)

    collect(fixed)

    if not polys:
        return MultiPolygon()
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)
```