"""Repair invalid Polygon/MultiPolygon geometries.

Provides `fix_geometry`, which converts an invalid (e.g. self-intersecting)
shapely Polygon or MultiPolygon into a valid geometry covering the same
region enclosed by the input's boundary rings.
"""

from shapely.geometry import MultiPolygon, Polygon
from shapely.validation import make_valid


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the region enclosed by `geom`.

    `geom` is a shapely Polygon or MultiPolygon that may be invalid (for
    example self-intersecting). The returned geometry is valid, covers
    every location enclosed by the input's boundary rings, and adds no
    extra area. If `geom` is already valid, a geometry covering the same
    region is returned unchanged.
    """
    if geom.is_valid:
        return geom

    fixed = make_valid(geom)

    if fixed.is_empty or not fixed.is_valid:
        fixed = geom.buffer(0)

    return _as_polygonal(fixed)


def _as_polygonal(geom):
    """Collapse `geom` (possibly a GeometryCollection) to Polygon/MultiPolygon.

    Non-polygonal components (stray points/lines that can appear in a
    make_valid result) carry no area and are dropped.
    """
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom

    polygons = []
    for part in getattr(geom, "geoms", []):
        resolved = _as_polygonal(part)
        if isinstance(resolved, Polygon):
            polygons.append(resolved)
        elif isinstance(resolved, MultiPolygon):
            polygons.extend(resolved.geoms)

    if not polygons:
        return MultiPolygon()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)