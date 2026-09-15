"""Repair of invalid polygonal geometries.

The single public entry point, :func:`fix_geometry`, turns a possibly invalid
``Polygon`` / ``MultiPolygon`` into a valid one covering exactly the region
enclosed by the input's boundary rings:

* every location enclosed by the input's boundary is covered by the result,
* no area outside that region is added,
* an already-valid input is returned unchanged.

The repair is ring-oriented rather than even-odd oriented.  A self-intersecting
shell such as a bow tie encloses *both* lobes, so both lobes survive; a lobe is
never dropped just because its winding direction disagrees with the rest of the
ring.  Interior rings keep their meaning as holes, so valid inputs with holes
round-trip unchanged.

Strategies are tried in order until one yields a valid polygonal geometry:

1. ``shapely.make_valid(..., method="structure")`` (GEOS ``GeometryFixer``),
2. an equivalent ring-by-ring repair written against ``buffer(0)`` only, for
   builds where the ``structure`` method is unavailable,
3. ``shapely.make_valid(...)`` with the default linework method, keeping only
   the polygonal output.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Union

import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["fix_geometry"]

Polygonal = Union[Polygon, MultiPolygon]


def fix_geometry(geom: Polygonal) -> Polygonal:
    """Return a valid ``Polygon``/``MultiPolygon`` for a possibly invalid one.

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon``.  It may be invalid, e.g.
        self-intersecting rings, overlapping parts, or holes that poke outside
        their shell.

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering exactly the region enclosed by the input's
        boundary rings.  Empty input gives empty output; zero-area input (a
        collapsed, line-like ring) gives an empty polygon, since it encloses no
        region.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    ValueError
        If the geometry could not be repaired by any strategy, e.g. because its
        coordinates are not finite.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry() expects a Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )

    if geom.is_empty:
        return _empty_like(geom)
    if geom.is_valid:
        return geom

    failures: List[Exception] = []
    for repair in (_make_valid_structure, _fix_ring_by_ring, _make_valid_linework):
        try:
            candidate = _as_polygonal(repair(geom))
        except Exception as exc:  # fall through to the next strategy
            failures.append(exc)
            continue
        if candidate is None:
            # Nothing polygonal survived: the input encloses no area.
            return _empty_like(geom)
        if candidate.is_valid:
            return candidate

    if failures:
        raise ValueError(f"could not repair geometry: {failures[0]}") from failures[0]
    raise ValueError("could not repair geometry")


# --------------------------------------------------------------------------
# repair strategies
# --------------------------------------------------------------------------


def _make_valid_structure(geom: Polygonal) -> Optional[BaseGeometry]:
    """Repair via GEOS' structured make-valid (shapely >= 2.1, GEOS >= 3.10).

    The structure method rebuilds the geometry from its rings — shells unioned,
    holes subtracted — which is exactly the "region enclosed by the boundary"
    semantics we want.  ``keep_collapsed=False`` drops line/point debris so the
    output stays polygonal.
    """
    return shapely.make_valid(geom, method="structure", keep_collapsed=False)


def _fix_ring_by_ring(geom: Polygonal) -> Optional[BaseGeometry]:
    """Portable equivalent of the structure method, using only ``buffer(0)``."""
    fixed = []
    for part in _iter_parts(geom):
        if not isinstance(part, Polygon):
            continue
        region = _fix_polygon_rings(part)
        if region is not None:
            fixed.append(region)
    if not fixed:
        return None
    return fixed[0] if len(fixed) == 1 else unary_union(fixed)


def _make_valid_linework(geom: Polygonal) -> Optional[BaseGeometry]:
    """Last resort: default make-valid, from which we keep the polygons."""
    return shapely.make_valid(geom)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _fix_polygon_rings(poly: Polygon) -> Optional[BaseGeometry]:
    """Region enclosed by one polygon's rings: shell minus its holes."""
    shell = _ring_region(poly.exterior)
    if shell is None:
        return None
    holes = [
        region
        for region in (_ring_region(ring) for ring in poly.interiors)
        if region is not None
    ]
    if holes:
        shell = shell.difference(holes[0] if len(holes) == 1 else unary_union(holes))
    return None if shell.is_empty else shell


def _ring_region(ring) -> Optional[BaseGeometry]:
    """Region enclosed by a single, possibly self-intersecting, ring.

    ``buffer(0)`` keeps the area whose winding is positive, so a lobe wound
    against the ring's dominant direction would be discarded.  Buffering both
    orientations and unioning the results keeps every enclosed lobe while still
    adding nothing outside the ring.
    """
    coords = list(ring.coords)
    if len(coords) < 4:  # fewer than 3 distinct vertices encloses no area
        return None

    regions = []
    for ordered in (coords, coords[::-1]):
        region = Polygon(ordered).buffer(0)
        if region is not None and not region.is_empty:
            regions.append(region)
    if not regions:
        return None
    return regions[0] if len(regions) == 1 else unary_union(regions)


def _iter_parts(geom: Optional[BaseGeometry]) -> Iterator[BaseGeometry]:
    """Yield the single-part geometries of ``geom``, recursing into collections."""
    if geom is None or geom.is_empty:
        return
    parts = getattr(geom, "geoms", None)
    if parts is None:
        yield geom
        return
    for part in parts:
        yield from _iter_parts(part)


def _as_polygonal(geom: Optional[BaseGeometry]) -> Optional[Polygonal]:
    """Reduce a repair result to a ``Polygon``/``MultiPolygon``, or ``None``.

    Non-polygonal debris (collapsed edges, isolated points) is discarded: it
    carries no area, so dropping it neither loses nor adds covered region.
    """
    polys = [
        part
        for part in _iter_parts(geom)
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if not polys:
        return None
    if len(polys) == 1 and polys[0].is_valid:
        return polys[0]

    merged = unary_union(polys)
    if isinstance(merged, (Polygon, MultiPolygon)):
        return None if merged.is_empty else merged

    parts = [
        part
        for part in _iter_parts(merged)
        if isinstance(part, Polygon) and not part.is_empty
    ]
    return MultiPolygon(parts) if parts else None


def _empty_like(geom: Polygonal) -> Polygonal:
    """An empty geometry of the same kind as ``geom``."""
    return MultiPolygon() if isinstance(geom, MultiPolygon) else Polygon()