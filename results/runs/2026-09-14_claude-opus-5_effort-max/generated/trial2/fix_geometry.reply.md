I couldn't run the module here (the sandbox declined both the write and the python run), so the code below is reasoned rather than executed — the design notes are in the docstrings.

```python
"""Repair invalid polygonal geometry without adding or dropping enclosed area.

``fix_geometry`` rebuilds a polygon from its own linework instead of relying on
``buffer(0)`` (which can silently discard oppositely-wound lobes of a
self-intersecting ring) or on bare ``make_valid`` (which can hand back a
``GeometryCollection`` containing dangling lines).

The rule applied is the one implied by the polygon data model:

* a point is inside a part when its winding number around the *shell* ring is
  non-zero, and
* its winding number around every *hole* ring is zero.

Non-zero winding (rather than even-odd) keeps regions that the boundary wraps
more than once, so no enclosed area is lost; testing hole rings separately
keeps real holes empty, so no new area is gained and an already-valid polygon
round-trips unchanged.
"""

import numpy as np
from shapely import force_2d, make_valid
from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the same region.

    ``geom`` may have a self-intersecting shell, holes that cross or escape the
    shell, or overlapping parts.  The result covers every location enclosed by
    the input's rings and nothing more.  Inputs that are already valid are
    returned unchanged; geometry that encloses no area returns an empty
    ``Polygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry() expects a Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )
    if geom.is_empty:
        return Polygon()
    if geom.is_valid:
        return geom

    try:
        faces = []
        for part in _parts(force_2d(geom)):
            faces.extend(_enclosed_faces(part))
        if not faces:
            return Polygon()
        return _as_polygonal(unary_union(faces))
    except GEOSException:
        # Pathological coordinates can defeat the overlay; fall back to GEOS'
        # own repair and keep just its polygonal output.
        return _as_polygonal(make_valid(geom))


def _parts(geom):
    return list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]


def _ring_coords(ring):
    """Closed ``(n, 2)`` vertex array for ``ring``, or ``None`` if degenerate."""
    if ring is None or ring.is_empty:
        return None
    coords = np.asarray(ring.coords, dtype=float)[:, :2]
    if len(coords) < 4:
        return None
    if not np.array_equal(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[:1]])
    return coords


def _enclosed_faces(poly):
    """Split one part into faces and keep those its rings actually enclose."""
    shell = _ring_coords(poly.exterior)
    if shell is None:
        return []
    holes = [c for c in map(_ring_coords, poly.interiors) if c is not None]

    # Unioning the rings nodes every self- and mutual intersection and dissolves
    # duplicated collinear edges, which is what the polygonizer needs.  Every
    # face it returns therefore has an interior free of linework, so a single
    # representative point classifies the whole face.
    noded = unary_union([LineString(c) for c in [shell] + holes])
    kept = []
    for face in polygonize(list(getattr(noded, "geoms", [noded]))):
        if face.is_empty:
            continue
        point = face.representative_point()
        x, y = point.x, point.y
        if _winding_number(x, y, shell) == 0:
            continue
        if any(_winding_number(x, y, hole) != 0 for hole in holes):
            continue
        kept.append(face)
    return kept


def _winding_number(x, y, ring):
    """Winding number of a closed ring about ``(x, y)``; zero when outside.

    Sunday's crossing test, vectorised: count upward edge crossings that pass
    left of the point minus downward crossings that pass right of it.  Points
    lying exactly on an edge give ``side == 0`` and contribute nothing, so the
    two halves of a zero-width spike cancel.
    """
    x0, y0 = ring[:-1, 0], ring[:-1, 1]
    x1, y1 = ring[1:, 0], ring[1:, 1]
    side = (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0)
    up = (y0 <= y) & (y1 > y) & (side > 0)
    down = (y0 > y) & (y1 <= y) & (side < 0)
    return int(np.count_nonzero(up)) - int(np.count_nonzero(down))


def _as_polygonal(geom):
    """Coerce an overlay result to a ``Polygon`` or ``MultiPolygon``."""
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    polys = _collect_polygons(geom)
    if not polys:
        return Polygon()
    merged = unary_union(polys)
    return merged if isinstance(merged, (Polygon, MultiPolygon)) else Polygon()


def _collect_polygons(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    out = []
    for part in getattr(geom, "geoms", ()):
        out.extend(_collect_polygons(part))
    return out
```