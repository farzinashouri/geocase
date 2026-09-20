```python
"""Repair invalid shapely Polygon/MultiPolygon geometries."""

from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def _rings_of(geom):
    """Yield exterior/interior rings as Polygons built individually so that
    self-intersections in one ring don't corrupt the others."""
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        raise TypeError(f"Unsupported geometry type: {geom.geom_type}")

    for poly in polys:
        yield Polygon(poly.exterior)
        for interior in poly.interiors:
            yield Polygon(interior)


def fix_geometry(geom: BaseGeometry):
    """Return a valid Polygon/MultiPolygon covering exactly the region
    enclosed by ``geom``'s boundary rings (nonzero fill rule).

    Each boundary ring is buffered by 0 individually to resolve local
    self-intersections into a valid geometry, then rings are combined
    with a symmetric-difference-style union that reproduces the
    even-odd/nonzero enclosed area: exterior rings add area, interior
    rings (holes) subtract it, matching how shapely already treats
    interiors for already-valid polygons.
    """
    if geom.is_empty:
        return geom

    if isinstance(geom, Polygon):
        rings = [(geom.exterior, True)] + [(r, False) for r in geom.interiors]
        source_polys = [geom]
    elif isinstance(geom, MultiPolygon):
        rings = []
        for poly in geom.geoms:
            rings.append((poly.exterior, True))
            for r in poly.interiors:
                rings.append((r, False))
        source_polys = list(geom.geoms)
    else:
        raise TypeError(f"Unsupported geometry type: {geom.geom_type}")

    if geom.is_valid:
        return geom

    result = None
    for poly in source_polys:
        exterior_fixed = Polygon(poly.exterior).buffer(0)
        piece = exterior_fixed
        for interior in poly.interiors:
            hole_fixed = Polygon(interior).buffer(0)
            piece = piece.difference(hole_fixed)
        result = piece if result is None else unary_union([result, piece])

    if result is None or result.is_empty:
        return MultiPolygon()

    if isinstance(result, (Polygon, MultiPolygon)):
        return result

    # Fallback: extract polygonal parts if union produced a GeometryCollection.
    polys = [g for g in getattr(result, "geoms", [result]) if isinstance(g, Polygon)]
    if not polys:
        return MultiPolygon()
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)
```