"""Repair invalid shapely Polygon/MultiPolygon geometries."""

from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
from shapely.ops import unary_union


def fix_geometry(geom):
    if geom.is_valid:
        return geom

    fixed = make_valid(geom)
    polygonal = unary_union(
        [g for g in _flatten(fixed) if isinstance(g, Polygon)]
    )

    if isinstance(polygonal, Polygon):
        return polygonal
    if isinstance(polygonal, MultiPolygon):
        return polygonal
    return MultiPolygon([])


def _flatten(geom):
    if geom.geom_type.startswith("Multi") or geom.geom_type == "GeometryCollection":
        for part in geom.geoms:
            yield from _flatten(part)
    else:
        yield geom