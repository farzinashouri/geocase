"""Repair invalid (e.g. self-intersecting) shapely polygons.

The repaired geometry covers exactly the region enclosed by the input's
boundary rings: for every polygon in the input, the region enclosed by its
exterior ring (under the non-zero winding rule, so both lobes of a "bowtie"
and doubly-wound regions are kept) minus the regions enclosed by its
interior rings.  Parts are unioned across polygons.  Already-valid input is
returned unchanged.
"""

from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["fix_geometry"]


def _winding_number(coords: np.ndarray, x: float, y: float) -> int:
    """Winding number of closed ring ``coords`` (N x 2) around point (x, y)."""
    x0, y0 = coords[:-1, 0], coords[:-1, 1]
    x1, y1 = coords[1:, 0], coords[1:, 1]
    # Signed area test: > 0 when the point is left of the directed edge.
    is_left = (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0)
    upward = (y0 <= y) & (y1 > y) & (is_left > 0)
    downward = (y0 > y) & (y1 <= y) & (is_left < 0)
    return int(np.count_nonzero(upward) - np.count_nonzero(downward))


def _ring_region(ring) -> BaseGeometry:
    """Valid polygonal region enclosed by a (possibly self-intersecting) ring."""
    coords = np.asarray(ring.coords, dtype=float)
    if coords.ndim != 2 or len(coords) < 4:
        return Polygon()
    coords = coords[:, :2]
    if not np.array_equal(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[:1]])

    # Node the ring's linework so every crossing becomes a vertex, then
    # extract every bounded face of the resulting planar arrangement.
    noded = shapely.unary_union(LineString(coords))
    faces = shapely.get_parts(shapely.polygonize(shapely.get_parts(noded)))

    kept = []
    for face in faces:
        if face.is_empty or face.area == 0:
            continue
        pt = face.representative_point()
        if _winding_number(coords, pt.x, pt.y) != 0:
            kept.append(face)
    if not kept:
        return Polygon()
    return shapely.unary_union(kept)


def _polygon_region(poly: Polygon) -> BaseGeometry:
    shell = _ring_region(poly.exterior)
    if shell.is_empty:
        return Polygon()
    holes = [_ring_region(h) for h in poly.interiors]
    holes = [h for h in holes if not h.is_empty]
    if holes:
        shell = shell.difference(shapely.unary_union(holes))
    return shell


def _polygonal_only(geom: BaseGeometry) -> BaseGeometry:
    """Keep only Polygon parts of ``geom`` and return a Polygon/MultiPolygon."""
    parts = [
        p
        for p in shapely.get_parts(geom)
        if isinstance(p, Polygon) and not p.is_empty and p.area > 0
    ]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    merged = shapely.unary_union(parts)
    if isinstance(merged, (Polygon, MultiPolygon)):
        return merged
    return _polygonal_only(merged)


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the region enclosed by ``geom``.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Possibly invalid input (self-intersections, crossing holes, ...).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry covering exactly the enclosed region of the input.
    """
    if geom is None:
        return Polygon()
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            f"fix_geometry expects a Polygon or MultiPolygon, got {type(geom).__name__}"
        )
    if geom.is_empty:
        return Polygon()
    if shapely.is_valid(geom):
        return geom

    regions = [_polygon_region(p) for p in shapely.get_parts(geom)]
    regions = [r for r in regions if not r.is_empty]
    if not regions:
        return Polygon()
    result = shapely.unary_union(regions)
    result = _polygonal_only(result)
    if not shapely.is_valid(result):
        result = _polygonal_only(shapely.make_valid(result))
    return result