"""Repair invalid shapely polygons without adding or dropping enclosed area.

The region enclosed by a ring is taken to be the union of every face bounded
by that ring once its self-intersections are noded (so a bowtie keeps both
lobes).  A polygon's region is its shell region minus its hole regions, and a
MultiPolygon's region is the union of its parts.
"""

from shapely import make_valid
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union


def _polygonal(geom):
    """Reduce any geometry to a Polygon or MultiPolygon, discarding lower-dimensional parts."""
    if geom is None or geom.is_empty:
        return Polygon()
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    parts = []
    for part in getattr(geom, "geoms", []):
        piece = _polygonal(part)
        if not piece.is_empty:
            parts.append(piece)
    if not parts:
        return Polygon()
    return _polygonal(unary_union(parts))


def _ring_area(coords):
    """Return the full area enclosed by a possibly self-intersecting ring."""
    coords = list(coords)
    if len(coords) < 4:
        return Polygon()
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    noded = unary_union(LineString(coords))
    faces = list(polygonize(noded))
    if not faces:
        return Polygon()
    return _polygonal(unary_union(faces))


def _fix_polygon(poly):
    shell = _ring_area(poly.exterior.coords)
    if shell.is_empty:
        return Polygon()
    holes = [_ring_area(ring.coords) for ring in poly.interiors]
    holes = [hole for hole in holes if not hole.is_empty]
    if holes:
        shell = _polygonal(shell.difference(unary_union(holes)))
    return shell


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering exactly the region enclosed by ``geom``."""
    if geom is None or geom.is_empty:
        return Polygon()
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        raise TypeError("fix_geometry expects a shapely Polygon or MultiPolygon")

    if geom.is_valid:
        return geom

    parts = [_fix_polygon(poly) for poly in polys]
    parts = [part for part in parts if not part.is_empty]
    result = _polygonal(unary_union(parts)) if parts else Polygon()

    if result.is_empty or not result.is_valid:
        fallback = _polygonal(make_valid(geom))
        if not fallback.is_empty and fallback.is_valid:
            return fallback
    return result