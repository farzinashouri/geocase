"""
A small module providing a single function `fix_geometry` that takes a
Shapely `Polygon` or `MultiPolygon` (possibly invalid) and returns a
valid geometry covering exactly the region enclosed by the input's
boundary rings.  The function uses Shapely 2.1's `polygonize` and
`unary_union` to reconstruct the geometry from its boundary lines.
"""

from __future__ import annotations

from shapely.geometry import (
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
)
from shapely.ops import polygonize, unary_union


def fix_geometry(geom: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
    """
    Return a valid geometry covering exactly the region enclosed by the
    input's boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which may be invalid (e.g. self‑intersecting).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry that covers the same area as the input's boundary
        rings, with no additional area added.

    Notes
    -----
    The function works by extracting all exterior and interior rings of
    the input geometry, converting them to line strings, polygonizing
    that network of lines, and then taking the unary union of the
    resulting polygons.  This guarantees that the output is valid and
    exactly matches the area enclosed by the input's boundary rings.
    """
    if geom.is_empty:
        return geom

    # Gather all rings (exterior and interior) as LineString objects
    lines: list[LineString] = []

    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        raise TypeError("Input must be a shapely Polygon or MultiPolygon")

    for poly in polygons:
        # Exterior ring
        lines.append(LineString(poly.exterior.coords))
        # Interior rings (holes)
        for interior in poly.interiors:
            lines.append(LineString(interior.coords))

    # Create a MultiLineString from all rings
    mls = MultiLineString(lines)

    # Polygonize the network of lines
    polys = list(polygonize(mls))

    # If no polygons were produced, return the original geometry
    if not polys:
        return geom

    # Union all polygons to form the final geometry
    result = unary_union(polys)

    return result