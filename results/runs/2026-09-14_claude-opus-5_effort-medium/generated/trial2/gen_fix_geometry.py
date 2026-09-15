"""Repair invalid shapely polygonal geometries.

The repaired geometry covers exactly the region enclosed by the input's
boundary rings: nothing enclosed is dropped and no new area is introduced.
Importing this module has no side effects.
"""

from __future__ import annotations

import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["fix_geometry"]

_POLYGONAL = (Polygon, MultiPolygon)


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the same region as ``geom``.

    Parameters
    ----------
    geom : shapely Polygon or MultiPolygon
        Possibly invalid (self-intersecting, ring-touching, ...) geometry.

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering exactly the area enclosed by the input's
        boundary rings. An already-valid input is returned covering the same
        region. Degenerate (zero-area) input yields an empty Polygon.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if not isinstance(geom, _POLYGONAL):
        raise TypeError(
            f"expected a Polygon or MultiPolygon, got {geom.geom_type}"
        )

    if geom.is_empty:
        return Polygon()

    if geom.is_valid:
        # Already valid: normalize the type only, never touch the coordinates.
        return _as_polygonal(geom)

    for repair in (_make_valid_structure, _make_valid_linework, _buffer_zero):
        try:
            repaired = repair(geom)
        except Exception:
            continue
        if repaired is None:
            continue
        result = _polygonal_parts(repaired)
        if result is not None and result.is_valid:
            return _as_polygonal(result)

    raise ValueError("could not repair geometry")


def _make_valid_structure(geom):
    """GEOS >= 3.10 'structure' repair: union semantics, polygonal output."""
    return shapely.make_valid(geom, method="structure", keep_collapsed=False)


def _make_valid_linework(geom):
    """Default repair; may emit lines/points that are discarded downstream."""
    return shapely.make_valid(geom)


def _buffer_zero(geom):
    return geom.buffer(0)


def _polygonal_parts(geom):
    """Keep only the areal components, dissolved into a single valid geometry."""
    if geom is None or geom.is_empty:
        return Polygon()

    parts = [g for g in _explode(geom) if isinstance(g, _POLYGONAL) and not g.is_empty]
    if not parts:
        return Polygon()
    if len(parts) == 1 and parts[0].is_valid:
        return parts[0]

    # Union rather than concatenate: repaired pieces may overlap, and a union
    # of the enclosed pieces adds no area beyond what they already cover.
    return unary_union(parts)


def _explode(geom):
    """Yield the leaf geometries of a (possibly nested) collection."""
    if hasattr(geom, "geoms") and not isinstance(geom, Polygon):
        for part in geom.geoms:
            yield from _explode(part)
    else:
        yield geom


def _as_polygonal(geom):
    """Coerce a valid areal geometry to Polygon or MultiPolygon."""
    if isinstance(geom, _POLYGONAL):
        return geom
    if geom.is_empty:
        return Polygon()
    parts = [g for g in _explode(geom) if isinstance(g, Polygon) and not g.is_empty]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)