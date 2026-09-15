"""Repair invalid shapely polygons.

``fix_geometry`` returns a valid ``Polygon``/``MultiPolygon`` covering exactly
the region enclosed by the input's boundary rings: nothing enclosed is lost and
no new area is introduced.
"""

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

__all__ = ["fix_geometry"]


def _polygonal_parts(geom):
    """Yield the Polygon components of an arbitrary geometry, dropping
    zero-area (line/point) leftovers that repair can produce."""
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)):
        for part in geom.geoms:
            yield from _polygonal_parts(part)
    # lines and points carry no area: ignore


def fix_geometry(geom):
    """Return a valid Polygon or MultiPolygon covering the same region as ``geom``.

    Parameters
    ----------
    geom : shapely Polygon or MultiPolygon
        May be invalid (self-intersecting rings, self-touching boundaries,
        overlapping parts, ...).

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering exactly the area enclosed by ``geom``'s
        boundary rings. An empty input yields an empty Polygon.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            f"expected a Polygon or MultiPolygon, got {geom.geom_type}"
        )

    if geom.is_empty:
        return Polygon()

    if geom.is_valid:
        # Still normalise multi-part inputs whose parts overlap or touch, so the
        # result is a clean, non-overlapping geometry covering the same region.
        repaired = geom
    else:
        # make_valid keeps every enclosed lobe of a self-intersecting ring and
        # never invents area outside the original boundary.
        repaired = make_valid(geom)

    parts = list(_polygonal_parts(repaired))
    if not parts:
        return Polygon()

    # unary_union merges touching/overlapping faces into a single valid cover.
    result = unary_union(parts)

    if isinstance(result, Polygon):
        return result
    if isinstance(result, MultiPolygon):
        return result

    parts = list(_polygonal_parts(result))
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)