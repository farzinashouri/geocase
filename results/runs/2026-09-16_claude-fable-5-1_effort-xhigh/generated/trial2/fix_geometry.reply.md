Sandbox permissions blocked writing and running a scratch test, so this module is unverified by execution here. It nodes each ring, polygonizes it, unions the faces, and subtracts the hole regions, which keeps every enclosed lobe and adds nothing.

```python
"""Repair invalid shapely polygons without losing or inventing area.

``fix_geometry`` returns a valid ``Polygon`` or ``MultiPolygon`` that covers
exactly the region enclosed by the input's rings: the union of everything
enclosed by each shell ring, minus the union of everything enclosed by each
hole ring.  Unlike ``buffer(0)`` (which drops lobes of a bow-tie) or the
default ``make_valid`` line-work strategy (which applies an even-odd rule and
can drop doubly-enclosed regions or promote stray holes to new polygons),
this keeps every enclosed location and adds nothing.
"""

from __future__ import annotations

from typing import Iterable, List, Union

import shapely
from shapely.errors import GEOSException
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiPolygon,
    Polygon,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["fix_geometry"]

Polygonal = Union[Polygon, MultiPolygon]


def fix_geometry(geom: Polygonal) -> Polygonal:
    """Return a valid polygonal geometry covering exactly the region of ``geom``.

    Every point enclosed by the input's boundary rings is covered by the
    result and no area outside the input's rings is added.  Valid input is
    returned unchanged.

    Raises:
        TypeError: if ``geom`` is not a shapely ``Polygon`` or ``MultiPolygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry expects a shapely Polygon or MultiPolygon, "
            f"got {type(geom).__name__}"
        )
    if geom.is_empty:
        return Polygon()
    if geom.is_valid:
        return geom

    try:
        return _rebuild(geom)
    except GEOSException:
        # Extremely degenerate input (e.g. nearly coincident noise segments)
        # can trip the noder; fall back to GEOS's own structural repair.
        return _fallback(geom)


# --------------------------------------------------------------------------
# Core rebuild: node each ring, polygonize it, union the faces.
# --------------------------------------------------------------------------


def _rebuild(geom: Polygonal) -> Polygonal:
    polygons = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    parts: List[BaseGeometry] = []
    for poly in polygons:
        if poly.is_empty:
            continue
        if poly.is_valid:
            parts.append(poly)
            continue
        shell = _ring_region(poly.exterior)
        if shell.is_empty:
            continue
        holes = [_ring_region(ring) for ring in poly.interiors]
        holes = [h for h in holes if not h.is_empty]
        if holes:
            shell = shell.difference(unary_union(holes))
        parts.append(shell)
    return _as_polygonal(unary_union(parts) if parts else Polygon())


def _ring_region(ring: LinearRing) -> BaseGeometry:
    """Union of every face enclosed by a single (possibly self-crossing) ring."""
    if ring.is_empty or len(ring.coords) < 4:
        return Polygon()
    line = LineString(ring.coords)
    if line.length == 0.0:
        return Polygon()
    noded = shapely.node(line)
    faces = shapely.polygonize([noded])
    if faces.is_empty:
        return Polygon()
    return _as_polygonal(unary_union(list(faces.geoms)))


# --------------------------------------------------------------------------
# Fallback and helpers.
# --------------------------------------------------------------------------


def _fallback(geom: Polygonal) -> Polygonal:
    try:
        repaired = shapely.make_valid(geom, method="structure", keep_collapsed=False)
    except (TypeError, GEOSException, ValueError):
        # Older GEOS without the structure method: line-work repair, then
        # keep only the areal parts.
        repaired = shapely.make_valid(geom)
    return _as_polygonal(repaired)


def _iter_polygons(geom: BaseGeometry) -> Iterable[Polygon]:
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)) or hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _iter_polygons(part)


def _as_polygonal(geom: BaseGeometry) -> Polygonal:
    """Coerce any geometry to a Polygon / MultiPolygon of its areal parts."""
    polys = [p for p in _iter_polygons(geom) if not p.is_empty and p.area > 0.0]
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    merged = unary_union(polys)
    if isinstance(merged, (Polygon, MultiPolygon)):
        return merged
    polys = [p for p in _iter_polygons(merged) if p.area > 0.0]
    if not polys:
        return Polygon()
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)
```