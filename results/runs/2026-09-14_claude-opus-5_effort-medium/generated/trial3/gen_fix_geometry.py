"""Repair invalid polygonal geometries.

Exposes :func:`fix_geometry`, which turns a possibly-invalid shapely
``Polygon``/``MultiPolygon`` into a valid one covering exactly the region
enclosed by the input's boundary rings.

Importing this module has no side effects.
"""

from __future__ import annotations

import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
from shapely.ops import unary_union

__all__ = ["fix_geometry"]


def _polygonal_parts(geom: BaseGeometry):
    """Yield every non-degenerate Polygon nested anywhere inside ``geom``.

    ``make_valid`` may hand back a GeometryCollection that also contains the
    lines/points left over from collapsed slivers; those carry no area and are
    dropped here.
    """
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        if geom.area > 0.0:
            yield geom
    elif isinstance(geom, BaseMultipartGeometry):
        for part in geom.geoms:
            yield from _polygonal_parts(part)


def _repair(geom: BaseGeometry) -> BaseGeometry:
    """Run GEOS MakeValid, falling back to a zero-width buffer."""
    try:
        # The default "linework" structure keeps *all* noded areas, so a
        # self-intersecting bow-tie comes back as both lobes rather than just
        # the larger one (which is what buffer(0) would give).
        return shapely.make_valid(geom)
    except Exception:
        return geom.buffer(0)


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` for ``geom``.

    The result covers exactly the region enclosed by the input's boundary
    rings: nothing enclosed by the input is dropped and no new area is added.
    A geometry that is already valid is returned covering the same region.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Possibly invalid input, e.g. with self-intersecting or misordered rings.

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry; an empty ``Polygon`` if the input encloses no area.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry() expects a Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )

    if geom.is_empty:
        return Polygon()

    repaired = geom if geom.is_valid else _repair(geom)

    parts = list(_polygonal_parts(repaired))
    if not parts:
        return Polygon()

    # Union merges the pieces MakeValid may have split apart (and any that
    # overlap, which would otherwise leave the result invalid) without changing
    # the covered region.
    result = parts[0] if len(parts) == 1 else unary_union(parts)

    if isinstance(result, Polygon):
        return result
    if isinstance(result, MultiPolygon):
        return result

    # unary_union of polygons is always polygonal, but stay defensive.
    survivors = list(_polygonal_parts(result))
    if not survivors:
        return Polygon()
    if len(survivors) == 1:
        return survivors[0]
    return MultiPolygon(survivors)