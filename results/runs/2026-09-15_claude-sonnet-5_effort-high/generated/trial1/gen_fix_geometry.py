"""Repair invalid Polygon/MultiPolygon geometries.

Uses shapely's OGC-standard make_valid to resolve self-intersections and
other invalidities, then unions the resulting polygonal pieces so the
output has no internal overlaps while covering exactly the area enclosed
by the original boundary rings.
"""

from typing import Iterator, Union

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

GeomT = Union[Polygon, MultiPolygon]


def _iter_polygons(geom: BaseGeometry) -> Iterator[Polygon]:
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)):
        for part in geom.geoms:
            yield from _iter_polygons(part)


def fix_geometry(geom: GeomT) -> GeomT:
    if geom.is_valid:
        return geom

    repaired = make_valid(geom)
    polygons = list(_iter_polygons(repaired))

    if not polygons:
        return MultiPolygon()

    merged = unary_union(polygons)

    if isinstance(merged, (Polygon, MultiPolygon)):
        return merged

    parts = list(_iter_polygons(merged))
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)