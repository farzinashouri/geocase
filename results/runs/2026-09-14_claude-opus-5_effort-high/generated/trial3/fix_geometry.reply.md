```python
"""Repair invalid shapely polygons.

``fix_geometry`` turns a (possibly invalid) ``Polygon`` / ``MultiPolygon`` into a
valid polygonal geometry that covers exactly the region enclosed by the input's
boundary rings: nothing enclosed is dropped, and no area is invented.

The repair is done by re-deriving each polygon from its own linework:

1. every ring is noded against itself (``unary_union``) and cut into the minimal
   set of faces (``polygonize``);
2. a face belongs to the ring's region when its winding number about that ring is
   non-zero.  The non-zero rule (rather than even-odd) is what keeps both lobes of
   a bow-tie and keeps regions that the ring wraps twice, while still excluding
   areas cut away by a slit;
3. the polygon is ``shell region - interior ring regions``, and the parts of a
   multipolygon are unioned so overlaps collapse instead of staying invalid.

``shapely.make_valid`` is used as a fallback for inputs whose linework is too
degenerate to polygonize.
"""

from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the region enclosed by
    ``geom``'s boundary rings.

    A geometry that is already valid is returned unchanged.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry() expects a shapely Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )
    if geom.is_empty:
        return geom
    if geom.is_valid:
        return geom

    parts = []
    incomplete = False
    for poly in _iter_polygons(geom):
        rebuilt = _rebuild_polygon(poly)
        if rebuilt is None:
            incomplete = True
            continue
        if not rebuilt.is_empty:
            parts.append(rebuilt)

    if incomplete or not parts:
        fallback = _make_valid_polygonal(geom)
        if fallback is not None and not fallback.is_empty:
            return fallback

    if not parts:
        return _as_polygonal(shapely.Polygon())

    merged = unary_union(parts) if len(parts) > 1 else parts[0]
    result = _as_polygonal(merged)

    if result.is_empty or not result.is_valid:
        fallback = _make_valid_polygonal(geom)
        if fallback is not None and not fallback.is_empty and fallback.is_valid:
            return fallback
    return result


# --------------------------------------------------------------------------- #
# per-polygon reconstruction
# --------------------------------------------------------------------------- #


def _rebuild_polygon(poly):
    """Rebuild one polygon from its rings, or ``None`` if that is not possible."""
    if poly.is_empty:
        return None
    if poly.is_valid:
        return poly

    shell = _ring_region(poly.exterior)
    if shell is None or shell.is_empty:
        return None

    holes = []
    for ring in poly.interiors:
        hole = _ring_region(ring)
        if hole is not None and not hole.is_empty:
            holes.append(hole)

    if holes:
        cut = unary_union(holes) if len(holes) > 1 else holes[0]
        shell = shell.difference(cut)

    region = _as_polygonal(shell)
    return None if region.is_empty else region


def _ring_region(ring):
    """Region enclosed by a single (possibly self-intersecting) closed ring.

    Returns ``None`` when the ring is degenerate (no enclosed area recoverable).
    """
    coords = np.asarray(ring.coords, dtype=float)
    if coords.shape[0] < 4:
        return None
    coords = coords[:, :2]
    if not np.all(np.isfinite(coords)):
        return None
    # ensure the ring is closed so the winding count is well defined
    if not np.array_equal(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[:1]])

    try:
        noded = unary_union(LineString(coords))
    except Exception:
        return None
    lines = _line_parts(noded)
    if not lines:
        return None

    try:
        faces = list(polygonize(lines))
    except Exception:
        return None
    faces = [f for f in faces if not f.is_empty and f.area > 0.0]
    if not faces:
        return None

    points = np.array(
        [[p.x, p.y] for p in (f.representative_point() for f in faces)], dtype=float
    )
    winding = _winding_numbers(coords, points)
    inside = [face for face, w in zip(faces, winding) if w != 0]
    if not inside:
        return None

    region = unary_union(inside) if len(inside) > 1 else inside[0]
    return region


def _winding_numbers(ring_coords, points):
    """Winding number of ``ring_coords`` about each point (vectorised crossings)."""
    x1 = ring_coords[:-1, 0]
    y1 = ring_coords[:-1, 1]
    x2 = ring_coords[1:, 0]
    y2 = ring_coords[1:, 1]

    px = points[:, 0][:, None]
    py = points[:, 1][:, None]

    # > 0 when the point lies left of the directed edge (x1,y1) -> (x2,y2)
    side = (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1)

    # half-open [y1, y2) tests so a vertex is counted exactly once
    upward = (y1 <= py) & (y2 > py) & (side > 0.0)
    downward = (y2 <= py) & (y1 > py) & (side < 0.0)
    return upward.sum(axis=1) - downward.sum(axis=1)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _iter_polygons(geom):
    if isinstance(geom, Polygon):
        if not geom.is_empty:
            yield geom
        return
    for part in geom.geoms:
        if isinstance(part, Polygon) and not part.is_empty:
            yield part


def _line_parts(geom):
    """Flatten ``geom`` into a list of ``LineString`` parts."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    parts = []
    geoms = getattr(geom, "geoms", None)
    if geoms is None:
        return []
    for part in geoms:
        parts.extend(_line_parts(part))
    return parts


def _polygon_parts(geom):
    """Flatten ``geom`` into a list of non-empty ``Polygon`` parts."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    geoms = getattr(geom, "geoms", None)
    if geoms is None:
        return []
    parts = []
    for part in geoms:
        parts.extend(_polygon_parts(part))
    return parts


def _as_polygonal(geom):
    """Coerce any geometry to ``Polygon`` or ``MultiPolygon`` (dropping lines/points)."""
    parts = [p for p in _polygon_parts(geom) if p.area > 0.0]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)


def _make_valid_polygonal(geom):
    """``shapely.make_valid`` fallback, reduced to polygonal output."""
    if not isinstance(geom, BaseGeometry):
        return None

    candidates = []
    try:
        candidates.append(shapely.make_valid(geom, method="structure"))
    except (TypeError, ValueError, shapely.errors.GEOSException):
        pass
    for attempt in (lambda: shapely.make_valid(geom), lambda: geom.buffer(0)):
        try:
            candidates.append(attempt())
        except Exception:
            continue

    for candidate in candidates:
        result = _as_polygonal(candidate)
        if not result.is_empty and result.is_valid:
            return result
    return None
```