```python
"""Fix invalid Polygon/MultiPolygon geometries.

Repairs self-intersecting or otherwise invalid shapely Polygon/MultiPolygon
geometries so that the returned geometry is valid while covering the same
region enclosed by the input's boundary rings.
"""

from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Polygon,
)
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid


def _extract_polygons(geom: BaseGeometry):
    """Yield all Polygon components contained in geom (any geometry type)."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)):
        for part in geom.geoms:
            yield from _extract_polygons(part)


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the region enclosed by geom's boundary.

    Args:
        geom: A shapely Polygon or MultiPolygon, possibly invalid
            (e.g. self-intersecting rings).

    Returns:
        A valid shapely Polygon or MultiPolygon covering exactly the area
        enclosed by the input's boundary rings.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("geom must be a shapely Polygon or MultiPolygon")

    if geom.is_valid:
        return geom

    repaired = make_valid(geom)

    polygons = [p for p in _extract_polygons(repaired) if not p.is_empty and p.area > 0]

    if not polygons:
        return Polygon()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)
```