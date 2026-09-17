"""Repair invalid shapely polygons without gaining or losing enclosed area.

The repair follows the "structure" strategy: every exterior ring is noded
against itself and polygonised, so every lobe of a bow-tie or figure-eight
survives (``buffer(0)`` would silently drop lobes with reversed winding).
Interior rings are repaired the same way and then subtracted, so a valid
polygon with holes round-trips to the same region.
"""

from __future__ import annotations

from typing import Iterable, List, Union

import shapely
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiPolygon,
    Polygon,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

PolygonLike = Union[Polygon, MultiPolygon]


def _polygons_of(geom: BaseGeometry) -> Iterable[Polygon]:
    """Yield the polygonal parts of any geometry, dropping lines and points."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon):
        yield from geom.geoms
    elif isinstance(geom, GeometryCollection):
        for part in geom.geoms:
            yield from _polygons_of(part)


def _ring_region(coords) -> BaseGeometry:
    """Return the region enclosed by one (possibly self-intersecting) ring.

    The ring is turned into a line, noded against itself via unary_union
    and polygonised. Every bounded face of the arrangement is enclosed by
    the ring, so their union is exactly the enclosed region.
    """
    coords = list(coords)
    if len(coords) < 4:
        return Polygon()
    line = LineString(coords)
    noded = unary_union(line)
    faces = list(polygonize(noded))
    if not faces:
        return Polygon()
    return unary_union(faces)


def _polygon_region(poly: Polygon) -> BaseGeometry:
    """Repair a single Polygon: union of shell region minus union of holes."""
    if poly.is_empty:
        return Polygon()
    shell = _ring_region(poly.exterior.coords)
    if shell.is_empty:
        return Polygon()
    holes = [_ring_region(ring.coords) for ring in poly.interiors]
    holes = [h for h in holes if not h.is_empty]
    if not holes:
        return shell
    return shell.difference(unary_union(holes))


def _as_polygonal(parts: List[Polygon]) -> PolygonLike:
    parts = [p for p in parts if not p.is_empty]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)


def fix_geometry(geom: PolygonLike) -> PolygonLike:
    """Return a valid Polygon/MultiPolygon covering the input's enclosed region.

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon``, possibly invalid
        (self-intersecting rings, overlapping parts, holes crossing shells).

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering exactly the area enclosed by the input's
        boundary rings. Already-valid input comes back covering the same
        region. Degenerate input (zero-area) yields an empty ``Polygon``.
    """
    if geom is None:
        return Polygon()
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            f"fix_geometry expects a Polygon or MultiPolygon, got {type(geom).__name__}"
        )
    if geom.is_empty:
        return Polygon()

    if geom.is_valid:
        return geom

    # Repair each polygon part independently, then union the repaired parts
    # so overlapping members of a MultiPolygon merge into one valid region.
    repaired = [_polygon_region(p) for p in _polygons_of(geom)]
    repaired = [r for r in repaired if not r.is_empty]
    if not repaired:
        return Polygon()
    merged = unary_union(repaired)

    result = _as_polygonal(list(_polygons_of(merged)))

    # Belt and braces: numerical edge cases can still leave an invalid
    # result; make_valid in "structure" mode preserves area the same way.
    if not result.is_valid:
        try:
            fixed = shapely.make_valid(result, method="structure", keep_collapsed=False)
        except TypeError:  # older shapely signature
            fixed = shapely.make_valid(result)
        result = _as_polygonal(list(_polygons_of(fixed)))

    return result


__all__ = ["fix_geometry"]