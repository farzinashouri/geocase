"""Repair invalid polygonal geometry.

``fix_geometry`` returns a valid ``Polygon``/``MultiPolygon`` covering exactly the
region enclosed by the input's boundary rings: nothing enclosed by the input is
dropped, and no area outside the input's boundary is introduced.

The region is rebuilt from the linework rather than with ``buffer(0)``, which
applies an even-odd style rule and can silently delete doubly-wound area.  Each
ring is noded, the resulting planar faces are polygonized, and the exterior's
faces are unioned; interior rings are treated as holes and differenced out, so a
valid input round-trips to the same region.

Importing this module has no side effects.
"""

from __future__ import annotations

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

try:  # shapely 2.1 exposes make_valid at the top level
    from shapely import make_valid as _make_valid
except ImportError:  # pragma: no cover - older layouts
    from shapely.validation import make_valid as _make_valid

__all__ = ["fix_geometry"]


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the region ``geom`` encloses.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Possibly invalid input (self-intersecting rings, self-touching shells,
        overlapping parts, holes crossing the shell, ...).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry covering every location enclosed by the input's
        boundary and no additional area.  Degenerate (zero-area) input yields an
        empty ``Polygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry expects a Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )

    if geom.is_empty:
        return Polygon()

    # An already-valid geometry is returned untouched: same region, no risk of
    # floating-point drift from a needless overlay.
    if geom.is_valid:
        return geom

    pieces = []
    for part in _polygon_parts(geom):
        fixed = _fix_polygon(part)
        if fixed is not None and not fixed.is_empty:
            pieces.append(fixed)

    if not pieces:
        return Polygon()

    result = pieces[0] if len(pieces) == 1 else _safe_union(pieces)
    result = _as_polygonal(result)

    # Paranoia: overlay output should already be valid, but never hand back an
    # invalid geometry.
    if not result.is_empty and not result.is_valid:
        result = _as_polygonal(_structure_make_valid(result))
    return result


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _polygon_parts(geom):
    """Yield the individual Polygon components of a polygonal geometry."""
    if isinstance(geom, Polygon):
        if not geom.is_empty:
            yield geom
        return
    for part in geom.geoms:
        yield from _polygon_parts(part)


def _fix_polygon(poly):
    """Rebuild a single Polygon as shell-faces minus hole-faces."""
    try:
        shell = _ring_region(poly.exterior)
        if shell is None or shell.is_empty:
            return None

        holes = []
        for interior in poly.interiors:
            hole = _ring_region(interior)
            if hole is not None and not hole.is_empty:
                holes.append(hole)

        if holes:
            shell = shell.difference(_safe_union(holes))
    except Exception:
        # GEOS can throw on pathological linework (robustness failures during
        # noding).  Fall back to the library repair rather than losing the part.
        return _as_polygonal(_structure_make_valid(poly))

    return None if shell.is_empty else shell


def _ring_region(ring):
    """Return the area enclosed by a single (possibly self-intersecting) ring.

    Self-intersections are noded so the ring becomes a planar graph; every
    bounded face of that graph is enclosed by the ring, so their union is the
    enclosed region.  Dangling edges (zero-area spikes) drop out naturally.
    """
    coords = list(ring.coords)
    if len(coords) < 4:
        return None

    line = LineString(coords)

    # Simple closed ring: already a well-formed polygon, skip the overlay.
    if line.is_simple:
        candidate = Polygon(coords)
        return None if candidate.is_empty else candidate

    faces = list(polygonize(_node(line)))
    if not faces:
        return None
    return _safe_union(faces)


def _node(line):
    """Split ``line`` at its self-intersections."""
    # Unioning the individual segments forces GEOS to node the linework; passing
    # a single geometry to unary_union can be short-circuited.
    coords = list(line.coords)
    segments = [
        LineString((a, b)) for a, b in zip(coords, coords[1:]) if a != b
    ]
    if not segments:
        return line
    return unary_union(segments)


def _safe_union(geoms):
    """Union polygonal geometries, retrying via make_valid on GEOS failures."""
    try:
        return unary_union(geoms)
    except Exception:
        repaired = [_structure_make_valid(g) for g in geoms]
        return unary_union(repaired)


def _structure_make_valid(geom):
    """``make_valid`` using the structure method when the build supports it."""
    try:
        return _make_valid(geom, method="structure", keep_collapsed=False)
    except (TypeError, ValueError):
        return _make_valid(geom)


def _as_polygonal(geom):
    """Coerce a repair result to Polygon/MultiPolygon, dropping lines/points."""
    if geom is None or geom.is_empty:
        return Polygon()
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return geom

    polygons = [p for p in _collect_polygons(geom)]
    if not polygons:
        return Polygon()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)


def _collect_polygons(geom):
    """Recursively yield non-empty Polygons from any geometry."""
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
        return
    for part in getattr(geom, "geoms", ()):
        yield from _collect_polygons(part)