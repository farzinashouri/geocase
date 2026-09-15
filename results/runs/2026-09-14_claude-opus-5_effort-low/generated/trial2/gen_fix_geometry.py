"""Repair invalid shapely polygons without changing the region they enclose.

``fix_geometry`` returns a valid ``Polygon``/``MultiPolygon`` covering the same
area as the input's boundary rings: an already-valid input round-trips to an
equal region, a self-intersecting one is resolved into valid parts, and no area
outside the input's rings is ever introduced.
"""

from __future__ import annotations

import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["fix_geometry"]


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` equivalent to ``geom``.

    Parameters
    ----------
    geom : shapely Polygon or MultiPolygon
        Possibly invalid input (self-intersections, rings touching, duplicate
        or unclosed-looking coordinate sequences, ...).

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering exactly the region enclosed by the input's
        exterior rings minus its interior rings. An empty ``Polygon`` is
        returned when the input encloses no area (empty or degenerate input).
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom)!r}")
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(f"expected Polygon or MultiPolygon, got {geom.geom_type}")

    if geom.is_empty:
        return Polygon()

    if geom.is_valid:
        # Already valid: nothing to repair, but normalise the container type so
        # callers get consistent output.
        return _as_polygonal(geom)

    repaired = _make_valid_structure(geom)
    if repaired is None or repaired.is_empty:
        # Fall back to the topology-preserving repair, then to buffer(0).
        repaired = shapely.make_valid(geom)
        if repaired.is_empty:
            repaired = geom.buffer(0)

    polygonal = _as_polygonal(repaired)
    if not polygonal.is_valid:
        # Very rare: re-node the result so the returned geometry is valid.
        polygonal = _as_polygonal(unary_union(polygonal))
    return polygonal


def _make_valid_structure(geom):
    """``make_valid`` with the structure method, or ``None`` if unavailable.

    The "structure" method interprets the input the way the task requires: the
    exterior rings are unioned and the interior rings are subtracted, so holes
    stay holes and self-intersection lobes are all kept. Collapsed (zero-area)
    parts are dropped, since they cover no region.
    """
    try:
        return shapely.make_valid(geom, method="structure", keep_collapsed=False)
    except (TypeError, ValueError, AttributeError):
        # Older shapely/GEOS without the structure method.
        return None


def _as_polygonal(geom):
    """Reduce ``geom`` to its polygonal content as a Polygon/MultiPolygon."""
    if geom.is_empty:
        return Polygon()
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        parts = [p for p in geom.geoms if not p.is_empty]
        if not parts:
            return Polygon()
        return parts[0] if len(parts) == 1 else MultiPolygon(parts)

    # GeometryCollection (or a lower-dimension geometry): keep only areal parts,
    # discarding the dangling lines/points a repair can emit.
    parts = [
        part
        for part in getattr(geom, "geoms", [])
        for part in (part.geoms if isinstance(part, MultiPolygon) else [part])
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)