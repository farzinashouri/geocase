"""Repair invalid polygonal geometry without losing or inventing area.

:func:`fix_geometry` rebuilds a (possibly self-intersecting) shapely
``Polygon``/``MultiPolygon`` from its own linework and returns a valid geometry
covering exactly the region its rings enclose.

Why not ``shapely.make_valid`` or the ``buffer(0)`` trick?  Both read
overlapping linework with an even-odd rule, so a ring that winds twice over the
same patch comes back with that patch punched out as a hole -- and ``buffer(0)``
may drop it altogether.  Here the faces of the noded linework are classified
with the *non-zero winding* rule instead: a face belongs to the result when the
ring winds around it at least once, in either direction.  Therefore

* every point the boundary winds around is covered by the result;
* no area outside the rings is ever added; and
* a sub-loop retraced in the opposite direction -- how a single ring encodes a
  hole -- keeps winding number zero and stays a hole, as do interior rings,
  which are subtracted rather than filled.

That last point is what lets an already-valid geometry come back unchanged.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Optional, Union

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid

__all__ = ["fix_geometry"]

Polygonal = Union[Polygon, MultiPolygon]


def fix_geometry(geom: Polygonal) -> Polygonal:
    """Return a valid geometry covering the region enclosed by ``geom``'s rings.

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon``, valid or not (self-
        intersecting rings, self-touching rings, overlapping parts, ...).

    Returns
    -------
    Polygon or MultiPolygon
        A valid geometry covering the same region: nothing enclosed by the
        input's boundary is dropped and no new area is introduced.  An empty or
        already-valid input is returned as is; a fully degenerate input (rings
        with no area) yields an empty ``Polygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry() expects a shapely Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )
    if geom.is_empty or geom.is_valid:
        return geom

    parts = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
    regions = [r for r in (_polygon_region(p) for p in parts) if not r.is_empty]
    if not regions:
        return Polygon()

    result = _as_polygonal(regions[0] if len(regions) == 1 else unary_union(regions))
    if not result.is_valid:  # belt and braces; the overlay ops above are exact
        result = _as_polygonal(make_valid(result))
    return result


def _polygon_region(poly: Polygon) -> Polygonal:
    """Region of a single (possibly invalid) polygon: shell fill minus holes."""
    shell = _ring_region(poly.exterior)
    if shell.is_empty:
        return shell

    holes = [h for h in (_ring_region(r) for r in poly.interiors) if not h.is_empty]
    if holes:
        cut = holes[0] if len(holes) == 1 else unary_union(holes)
        shell = shell.difference(cut)
    return _as_polygonal(shell)


def _ring_region(ring) -> Polygonal:
    """Region a single closed ring encloses, under the non-zero winding rule."""
    coords = _ring_coords(ring)
    if coords is None:
        return Polygon()

    # unary_union nodes the ring at its self-intersections and dissolves any
    # doubled (retraced) edges, which is what polygonize needs to see.
    noded = unary_union(LineString(coords))

    inside: List[Polygon] = []
    for face in polygonize(noded):
        # A face whose boundary retraces an edge comes back invalid; splitting
        # it first keeps representative_point() safely in the interior.
        pieces = _polygons(face) if face.is_valid else _polygons(make_valid(face))
        for piece in pieces:
            point = piece.representative_point()
            if _winding_number(coords, point.x, point.y) != 0:
                inside.append(piece)

    if not inside:
        return Polygon()
    return _as_polygonal(inside[0] if len(inside) == 1 else unary_union(inside))


def _ring_coords(ring) -> Optional[np.ndarray]:
    """Closed ``(n, 2)`` array of ring vertices, or ``None`` if degenerate."""
    if ring is None or ring.is_empty:
        return None
    coords = [(float(c[0]), float(c[1])) for c in ring.coords]  # drop any z
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    if len(coords) < 4:
        return None
    return np.asarray(coords, dtype=float)


def _winding_number(coords: np.ndarray, px: float, py: float) -> int:
    """Winding number of the closed ring ``coords`` around a point not on it."""
    x0, y0 = coords[:-1, 0], coords[:-1, 1]
    x1, y1 = coords[1:, 0], coords[1:, 1]
    # > 0 when the point lies left of the directed edge (x0, y0) -> (x1, y1).
    side = (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)
    up = np.count_nonzero((y0 <= py) & (y1 > py) & (side > 0))
    down = np.count_nonzero((y0 > py) & (y1 <= py) & (side < 0))
    return int(up) - int(down)


def _polygons(geom: Optional[BaseGeometry]) -> List[Polygon]:
    """Flatten any geometry to its non-degenerate polygonal parts."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > 0.0 else []
    return [p for part in getattr(geom, "geoms", ()) for p in _polygons(part)]


def _as_polygonal(geom: BaseGeometry) -> Polygonal:
    """Coerce a geometry to a ``Polygon``/``MultiPolygon`` (empty if neither)."""
    polys = _polygons(geom)
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)