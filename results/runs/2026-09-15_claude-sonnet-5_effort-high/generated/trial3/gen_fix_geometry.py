"""Repair invalid Polygon/MultiPolygon geometries so they cover exactly
the region enclosed by their boundary rings, using GEOS' MakeValid."""

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.validation import make_valid


def _polygonal_parts(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if isinstance(geom, GeometryCollection):
        parts = []
        for sub in geom.geoms:
            parts.extend(_polygonal_parts(sub))
        return parts
    # Points, LineStrings, etc. carry no area and are discarded.
    return []


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the same area as
    the region enclosed by ``geom``'s boundary rings.

    ``geom`` must be a shapely Polygon or MultiPolygon, possibly
    invalid (e.g. self-intersecting). If it is already valid, it is
    returned unchanged.
    """
    if geom.is_valid:
        return geom

    repaired = make_valid(geom)

    parts = []
    for part in _polygonal_parts(repaired):
        if isinstance(part, MultiPolygon):
            parts.extend(part.geoms)
        else:
            parts.append(part)

    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)