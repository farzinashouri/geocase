"""Repair invalid polygonal geometry without changing the region it encloses.

The public entry point is :func:`fix_geometry`, which turns a possibly invalid
``Polygon``/``MultiPolygon`` into a valid one covering exactly the region
enclosed by the input's boundary rings.

The repair is done by re-building the geometry from its own linework:

1. every ring of the input is noded against every other ring of the same part,
2. the noded linework is polygonized into a set of disjoint faces,
3. each face is kept when its winding number with respect to the part's rings
   is non-zero (shells counted counter-clockwise, holes clockwise),
4. the kept faces are unioned back together.

The non-zero winding rule is what makes the result "exactly the enclosed
region": a lobe that the boundary wraps twice (a self-overlapping flag) stays
filled, while a hole drawn as part of a self-touching shell stays empty, and
the two lobes of a bow-tie are both kept even though their windings have
opposite signs.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]


def _ring_coords(ring) -> np.ndarray:
    """Return a closed (n, 2) float array of a ring's coordinates."""
    coords = np.asarray(ring.coords, dtype=float)[:, :2]
    if len(coords) and not np.array_equal(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[:1]])
    return coords


def _signed_area(coords: np.ndarray) -> float:
    """Shoelace area; positive when the ring is counter-clockwise."""
    if len(coords) < 4:
        return 0.0
    x, y = coords[:, 0], coords[:, 1]
    return 0.5 * float(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))


def _winding_number(x: float, y: float, coords: np.ndarray) -> int:
    """Winding number of a closed ring around a point not lying on the ring."""
    if len(coords) < 4:
        return 0
    x1, y1 = coords[:-1, 0], coords[:-1, 1]
    x2, y2 = coords[1:, 0], coords[1:, 1]
    # Positive when the point lies left of the directed edge.
    side = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)
    upward = (y1 <= y) & (y2 > y) & (side > 0)
    downward = (y2 <= y) & (y1 > y) & (side < 0)
    return int(np.count_nonzero(upward) - np.count_nonzero(downward))


def _part_rings(polygon: Polygon) -> list[np.ndarray]:
    """Rings of one polygon, oriented CCW for the shell and CW for the holes.

    Orientation is normalised so that windings of shell and holes cancel inside
    holes.  A ring with zero signed area (a bow-tie shell, say) has no
    meaningful orientation; either choice gives the same non-zero test, so the
    fallback is arbitrary.
    """
    rings: list[np.ndarray] = []

    shell = _ring_coords(polygon.exterior)
    if _signed_area(shell) < 0:
        shell = shell[::-1]
    rings.append(shell)

    for interior in polygon.interiors:
        hole = _ring_coords(interior)
        if _signed_area(hole) > 0:
            hole = hole[::-1]
        rings.append(hole)

    return rings


def _polygonal(geom):
    """Keep only the polygonal content of a geometry."""
    if geom.is_empty:
        return Polygon()
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]
    if not parts:
        return Polygon()
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


def _fix_part(polygon: Polygon):
    """Rebuild a single (possibly invalid) polygon from its own linework."""
    rings = _part_rings(polygon)
    noded = unary_union([Polygon(r).exterior for r in rings if len(r) >= 4])
    if noded.is_empty:
        return Polygon()

    kept = []
    for face in polygonize(noded):
        if face.is_empty:
            continue
        # representative_point() is guaranteed to be in the face's interior,
        # and face interiors contain no ring segments, so the winding number
        # is well defined there.
        point = face.representative_point()
        px, py = point.x, point.y
        winding = sum(_winding_number(px, py, ring) for ring in rings)
        if winding != 0:
            kept.append(face)

    if not kept:
        return Polygon()
    return _polygonal(unary_union(kept))


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the same region.

    Parameters
    ----------
    geom : shapely Polygon or MultiPolygon
        Geometry that may be invalid, for example self-intersecting.

    Returns
    -------
    shapely Polygon or MultiPolygon
        A valid geometry covering exactly the region enclosed by the input's
        boundary rings: nothing enclosed is dropped and no area is added.
        An empty polygon is returned when the input encloses no area.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            f"expected a Polygon or MultiPolygon, got {type(geom).__name__}"
        )
    if geom.is_empty:
        return geom
    if geom.is_valid:
        return geom

    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]

    # Parts are repaired independently and unioned afterwards: windings must
    # not cancel across parts, or a hole in one part could punch away area
    # covered by another.
    fixed = [f for f in (_fix_part(p) for p in parts) if not f.is_empty]
    if not fixed:
        return Polygon()
    if len(fixed) == 1:
        return _polygonal(fixed[0])
    return _polygonal(unary_union(fixed))