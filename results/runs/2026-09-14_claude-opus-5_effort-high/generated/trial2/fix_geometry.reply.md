```python
"""Repair invalid polygonal geometries.

The single public entry point, :func:`fix_geometry`, turns a possibly invalid
shapely ``Polygon``/``MultiPolygon`` into a valid one that covers exactly the
region enclosed by the input's rings: shell rings are treated as filled curves
(so every point they enclose is kept, including lobes of a self-intersecting
"bowtie" and regions the ring wraps around more than once), and interior rings
are subtracted as holes.  No area outside the input's rings is ever added.

Importing this module has no side effects.
"""

from __future__ import annotations

import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]

_EMPTY = Polygon()

# ``make_valid(..., method="structure")`` needs GEOS 3.10+; older builds use the
# hand-rolled noding/polygonizing fallback below, which follows the same rules.
_HAS_STRUCTURE_METHOD = shapely.geos_version >= (3, 10, 0)


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the same region as ``geom``.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry to repair.  It may be invalid (self-intersecting rings,
        overlapping parts, rings touching themselves, ...).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry covering exactly the region enclosed by ``geom``'s
        shell rings, minus its interior rings.  Degenerate (zero-area) inputs
        yield an empty ``Polygon``.

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
        return _EMPTY

    # A valid input already satisfies the contract; hand it back untouched.
    if geom.is_valid:
        return geom

    repaired = _EMPTY
    if _HAS_STRUCTURE_METHOD:
        try:
            repaired = shapely.make_valid(
                geom, method="structure", keep_collapsed=False
            )
        except (TypeError, ValueError, shapely.errors.GEOSException):
            repaired = _EMPTY

    repaired = _polygonal(repaired)

    # Fall back to explicit noding + polygonizing when GEOS is too old, refused
    # the geometry, or collapsed something that clearly has area.
    if repaired.is_empty:
        repaired = _polygonal(_repair_by_polygonize(geom))

    return repaired


def _repair_by_polygonize(geom):
    """Rebuild ``geom`` from its rings: union of filled shells minus filled holes."""
    parts = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    fixed = []
    for part in parts:
        if part.is_empty:
            continue
        shell = _filled_ring(part.exterior)
        if shell.is_empty:
            continue
        holes = [_filled_ring(ring) for ring in part.interiors]
        holes = [h for h in holes if not h.is_empty]
        if holes:
            shell = shell.difference(unary_union(holes))
        if not shell.is_empty:
            fixed.append(shell)

    if not fixed:
        return _EMPTY
    return unary_union(fixed)


def _filled_ring(ring):
    """Return the region enclosed by ``ring``, treating it as a filled closed curve.

    The ring is noded against itself and the resulting faces are unioned, so a
    self-intersecting ring contributes every area it encloses exactly once.
    """
    coords = list(ring.coords)
    if len(coords) < 4:
        return _EMPTY
    try:
        # unary_union on a single line nodes it at its self-intersections.
        noded = unary_union(LineString(coords))
        faces = list(polygonize(noded))
    except shapely.errors.GEOSException:
        return _EMPTY
    if not faces:
        return _EMPTY
    return unary_union(faces)


def _polygonal(geom):
    """Coerce ``geom`` to a valid ``Polygon``/``MultiPolygon``, dropping lower dimensions."""
    if geom is None or geom.is_empty:
        return _EMPTY

    polygons = []
    _collect_polygons(geom, polygons)
    if not polygons:
        return _EMPTY
    if len(polygons) == 1:
        result = polygons[0]
    else:
        result = MultiPolygon(polygons)

    if not result.is_valid:
        result = unary_union(polygons)
        cleaned = []
        _collect_polygons(result, cleaned)
        if not cleaned:
            return _EMPTY
        result = cleaned[0] if len(cleaned) == 1 else MultiPolygon(cleaned)

    return result


def _collect_polygons(geom, out):
    """Append every non-empty ``Polygon`` inside ``geom`` to ``out``."""
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        out.append(geom)
    elif hasattr(geom, "geoms"):
        for sub in geom.geoms:
            _collect_polygons(sub, out)
```