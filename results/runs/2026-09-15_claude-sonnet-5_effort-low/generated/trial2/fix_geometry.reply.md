```python
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid


def fix_geometry(geom):
    if geom.is_valid:
        return geom

    fixed = make_valid(geom)
    fixed = _extract_polygonal(fixed)
    return fixed


def _extract_polygonal(geom: BaseGeometry):
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom

    polygons = []
    for part in getattr(geom, "geoms", []):
        if isinstance(part, Polygon):
            polygons.append(part)
        elif isinstance(part, MultiPolygon):
            polygons.extend(part.geoms)

    if not polygons:
        return Polygon()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)
```