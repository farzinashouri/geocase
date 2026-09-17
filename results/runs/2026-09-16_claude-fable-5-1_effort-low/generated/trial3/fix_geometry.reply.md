```python
"""Repair invalid shapely polygons without gaining or losing enclosed area.

`fix_geometry` rebuilds a (possibly self-intersecting) Polygon or
MultiPolygon from its boundary rings. For each polygon it:

1. nodes the exterior ring against itself and polygonizes the result,
   then unions every resulting face -> the full region enclosed by the
   exterior ring (a bow-tie yields both lobes, an overlapping loop keeps
   the doubly-wound part, a spiral fills in);
2. does the same for each interior ring -> the region enclosed by holes;
3. returns (exterior region) minus (hole regions).

For a valid input this reproduces the same region exactly. For an invalid
input every point enclosed by the exterior boundary is kept, nothing
outside it is added, and holes remove only what they enclose.
"""

from __future__ import annotations

import shapely
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiPolygon,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

__all__ = ["fix_geometry"]


def _polygonal_parts(geom: BaseGeometry) -> list[Polygon]:
    """Extract every Polygon from any geometry (dropping lines/points)."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if isinstance(geom, GeometryCollection) or hasattr(geom, "geoms"):
        out: list[Polygon] = []
        for g in geom.geoms:
            out.extend(_polygonal_parts(g))
        return out
    return []


def _region_enclosed_by_ring(ring: LinearRing | LineString) -> BaseGeometry:
    """Union of all faces bounded by a (possibly self-intersecting) ring."""
    if ring is None or ring.is_empty:
        return Polygon()
    line = LineString(ring.coords)
    # Fast path: a simple ring encloses exactly the polygon it delimits.
    if line.is_simple:
        poly = Polygon(line.coords)
        if poly.is_valid:
            return poly
    # Node the ring against itself, polygonize all faces, union them.
    noded = shapely.unary_union(line)
    faces = shapely.polygonize(
        list(noded.geoms) if hasattr(noded, "geoms") else [noded]
    )
    parts = _polygonal_parts(faces)
    if not parts:
        return Polygon()
    return shapely.unary_union(parts)


def _fix_polygon(poly: Polygon) -> BaseGeometry:
    if poly.is_empty:
        return Polygon()
    if poly.is_valid:
        return poly
    exterior = _region_enclosed_by_ring(poly.exterior)
    if exterior.is_empty:
        return Polygon()
    holes = [_region_enclosed_by_ring(r) for r in poly.interiors]
    holes = [h for h in holes if not h.is_empty]
    if not holes:
        return exterior
    hole_region = shapely.unary_union(holes)
    return exterior.difference(hole_region)


def _coerce(geom: BaseGeometry) -> Polygon | MultiPolygon:
    parts = [p for p in _polygonal_parts(geom) if not p.is_empty]
    if not parts:
        return Polygon()
    merged = shapely.unary_union(parts)
    parts = [p for p in _polygonal_parts(merged) if not p.is_empty]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        result: Polygon | MultiPolygon = parts[0]
    else:
        result = MultiPolygon(parts)
    if not result.is_valid:
        # Last resort for numerically awkward results; keeps the region.
        result = _coerce_valid(shapely.make_valid(result))
    return result


def _coerce_valid(geom: BaseGeometry) -> Polygon | MultiPolygon:
    parts = [p for p in _polygonal_parts(geom) if not p.is_empty]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)


def fix_geometry(geom: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
    """Return a valid Polygon/MultiPolygon covering exactly the region
    enclosed by ``geom``'s boundary rings.

    Parameters
    ----------
    geom : shapely.Polygon or shapely.MultiPolygon
        Possibly invalid input (self-intersections, self-touching rings,
        overlapping members, etc.).

    Returns
    -------
    shapely.Polygon or shapely.MultiPolygon
        A valid geometry. Every location enclosed by the input boundary is
        covered; no area outside the input's boundary is added. Valid
        inputs are returned unchanged.
    """
    if geom is None:
        raise TypeError("fix_geometry expects a Polygon or MultiPolygon, got None")
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            f"fix_geometry expects a Polygon or MultiPolygon, got {type(geom).__name__}"
        )
    if geom.is_empty:
        return geom
    if geom.is_valid:
        return geom

    if isinstance(geom, Polygon):
        fixed = _fix_polygon(geom)
    else:
        fixed_parts = [_fix_polygon(p) for p in geom.geoms]
        fixed = shapely.unary_union([f for f in fixed_parts if not f.is_empty]) \
            if fixed_parts else Polygon()

    return _coerce(fixed)
```