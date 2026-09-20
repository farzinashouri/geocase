"""Repair invalid shapely polygons without adding or dropping enclosed area.

`fix_geometry` returns a valid Polygon or MultiPolygon covering exactly the
region enclosed by the input's rings: shells are treated as areas (their
union is kept, so self-overlapping or figure-eight shells lose nothing), and
holes are subtracted. Valid input is returned covering the same region.
"""

from __future__ import annotations

from typing import Union

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

PolygonLike = Union[Polygon, MultiPolygon]

__all__ = ["fix_geometry"]


def _polygonal_parts(geom: BaseGeometry) -> list[Polygon]:
    """Flatten any geometry into its non-empty Polygon components."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [p for p in geom.geoms if not p.is_empty]
    if isinstance(geom, GeometryCollection) or hasattr(geom, "geoms"):
        parts: list[Polygon] = []
        for sub in geom.geoms:
            parts.extend(_polygonal_parts(sub))
        return parts
    # Points and lines carry no area; drop them.
    return []


def _as_polygonal(parts: list[Polygon]) -> PolygonLike:
    """Combine polygon parts into a single valid Polygon or MultiPolygon."""
    if not parts:
        return Polygon()
    merged = unary_union(parts) if len(parts) > 1 else parts[0]
    merged_parts = _polygonal_parts(merged)
    if not merged_parts:
        return Polygon()
    if len(merged_parts) == 1:
        return merged_parts[0]
    return MultiPolygon(merged_parts)


def _repair(geom: PolygonLike) -> BaseGeometry:
    """Run GEOS make_valid, preferring the area-preserving 'structure' method."""
    try:
        # 'structure' unions shell interiors and subtracts holes, so every
        # location enclosed by a ring is kept and no new area appears.
        # keep_collapsed=False discards degenerate line/point remnants.
        return make_valid(geom, method="structure", keep_collapsed=False)
    except TypeError:
        # Older shapely without the method/keep_collapsed keywords.
        return make_valid(geom)


def fix_geometry(geom: PolygonLike) -> PolygonLike:
    """Return a valid Polygon/MultiPolygon covering the region enclosed by `geom`.

    Parameters
    ----------
    geom:
        A shapely Polygon or MultiPolygon, possibly invalid (self-intersecting
        shells, overlapping components, misplaced holes, ...).

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering exactly the area enclosed by the input's
        boundary rings. An empty Polygon is returned for empty input.

    Raises
    ------
    TypeError
        If `geom` is not a Polygon or MultiPolygon.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            f"fix_geometry expects a Polygon or MultiPolygon, got {type(geom).__name__}"
        )

    if geom.is_empty:
        return Polygon()

    if geom.is_valid:
        # Already valid: normalise the container type but keep the same region.
        return _as_polygonal(_polygonal_parts(geom))

    repaired = _repair(geom)
    result = _as_polygonal(_polygonal_parts(repaired))

    if result.is_empty or not result.is_valid:
        # Defensive fallback: buffer(0) is the classic repair; combine it with
        # the structured result so no enclosed region is lost.
        fallback_parts = _polygonal_parts(geom.buffer(0))
        result = _as_polygonal(_polygonal_parts(result) + fallback_parts)

    return result