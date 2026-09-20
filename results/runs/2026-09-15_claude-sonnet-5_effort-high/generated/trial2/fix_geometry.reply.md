```python
"""Repair invalid Polygon/MultiPolygon geometries.

Recomputes a valid polygonal geometry from a possibly self-intersecting
(or otherwise invalid) ``Polygon``/``MultiPolygon`` so that every location
enclosed by the input's boundary rings is covered by the result, and no
extra area is introduced.
"""

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid


def fix_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Return a valid Polygon/MultiPolygon covering the area enclosed by ``geom``.

    If ``geom`` is already valid it is returned unchanged. Otherwise the
    geometry is repaired with GEOS's ``make_valid`` and reduced to its
    polygonal (area-bearing) components, dissolving away any duplicate or
    overlapping fragments that repair strategies can introduce.
    """
    if geom.is_valid:
        return geom

    repaired = _extract_polygonal(_make_valid_polygonal(geom))

    if not repaired.is_valid:
        # Extremely defensive fallback: buffer(0) is a long-standing GEOS
        # trick for coercing an invalid polygonal geometry into a valid one.
        buffered = geom.buffer(0)
        candidate = _extract_polygonal(buffered)
        if candidate.is_valid:
            repaired = candidate

    return repaired


def _make_valid_polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Run GEOS make_valid, preferring the area-preserving 'structure' method."""
    try:
        return make_valid(geom, method="structure", keep_collapsed=False)
    except TypeError:
        # Older shapely/GEOS combinations may not support the method /
        # keep_collapsed keywords.
        return make_valid(geom)


def _extract_polygonal(geometry: BaseGeometry) -> BaseGeometry:
    """Collapse a geometry (possibly a GeometryCollection) to its polygonal parts."""
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry

    if isinstance(geometry, GeometryCollection):
        polys = [g for g in geometry.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polys:
            return Polygon()
        return unary_union(polys)

    return Polygon()
```