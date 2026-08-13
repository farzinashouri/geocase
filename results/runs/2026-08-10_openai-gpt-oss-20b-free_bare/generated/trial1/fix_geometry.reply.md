```python
# -*- coding: utf-8 -*-
"""
A small module providing a single function `fix_geometry` that takes a
Shapely `Polygon` or `MultiPolygon` (possibly invalid) and returns a
valid geometry covering exactly the region enclosed by the input's
boundary rings.  The function uses Shapely 2.1's geometry and
operations; no side effects occur on import.
"""

from __future__ import annotations

from typing import Iterable

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import polygonize, unary_union


def _signed_area(poly: Polygon) -> float:
    """
    Compute the signed area of a simple polygon.
    Positive area indicates counter‑clockwise orientation (outer ring),
    negative area indicates clockwise orientation (hole).
    """
    coords = list(poly.exterior.coords)
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        area += (x1 * y2 - x2 * y1)
    return area / 2.0


def _classify_polygons(polys: Iterable[Polygon]) -> tuple[list[Polygon], list[Polygon]]:
    """
    Split polygons into outer (counter‑clockwise) and hole (clockwise)
    based on signed area.
    """
    outer, holes = [], []
    for p in polys:
        if _signed_area(p) > 0:
            outer.append(p)
        else:
            holes.append(p)
    return outer, holes


def fix_geometry(geom: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
    """
    Return a valid Shapely geometry covering exactly the region
    enclosed by the input's boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which may be invalid.

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry covering the same area as the input.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("Input must be a shapely Polygon or MultiPolygon")

    # If already valid, return unchanged
    if geom.is_valid:
        return geom

    # Polygonize the boundary lines to obtain simple polygons
    boundary = geom.boundary
    polys = list(polygonize(boundary))
    if not polys:
        # Fallback: return the original geometry (may be empty)
        return geom

    # Classify polygons into outer rings and holes
    outer_polys, hole_polys = _classify_polygons(polys)

    # Union of outer polygons
    outer_union = unary_union(outer_polys)

    # Subtract holes if any
    if hole_polys:
        hole_union = unary_union(hole_polys)
        result = outer_union.difference(hole_union)
    else:
        result = outer_union

    # Ensure the result is a Polygon or MultiPolygon
    if result.geom_type == "GeometryCollection":
        # Extract polygons from the collection
        polys_in_gc = [g for g in result.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if polys_in_gc:
            result = unary_union(polys_in_gc)

    # If the input was a single Polygon but the result is a MultiPolygon
    # with one part, return that part for consistency.
    if isinstance(geom, Polygon) and isinstance(result, MultiPolygon) and len(result.geoms) == 1:
        return result.geoms[0]

    return result
```