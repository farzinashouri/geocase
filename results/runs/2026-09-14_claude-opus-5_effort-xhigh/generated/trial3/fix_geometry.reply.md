```python
"""Repair invalid polygonal geometry.

``fix_geometry`` takes a shapely ``Polygon`` or ``MultiPolygon`` that may be
invalid (self-intersecting rings, overlapping parts, holes crossing the shell,
...) and returns a valid ``Polygon`` or ``MultiPolygon`` covering exactly the
region enclosed by the input's rings.

The region is defined ring-structurally: for every polygon part, the area
enclosed by its exterior ring minus the area enclosed by its interior rings,
with all parts unioned together.  The area "enclosed" by a ring that crosses
itself is taken to be the union of every face that ring bounds, so no enclosed
location is dropped and no area outside the rings is invented.  Valid input is
returned unchanged.

Importing this module has no side effects.
"""

from __future__ import annotations

import shapely
from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]

_POLYGONAL = ("Polygon", "MultiPolygon")
_COLLECTIONS = ("MultiPolygon", "GeometryCollection")


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the region enclosed
    by ``geom``'s rings.

    Parameters
    ----------
    geom : shapely.Polygon or shapely.MultiPolygon
        Geometry to repair.  May be invalid.

    Returns
    -------
    shapely.Polygon or shapely.MultiPolygon
        A valid geometry covering the same region.  An empty ``Polygon`` is
        returned when the input encloses no area.
    """
    if geom is None or not hasattr(geom, "geom_type"):
        raise TypeError("fix_geometry() expects a shapely Polygon or MultiPolygon")
    if geom.geom_type not in _POLYGONAL and geom.geom_type != "GeometryCollection":
        raise TypeError(
            "fix_geometry() expects a shapely Polygon or MultiPolygon, "
            f"got {geom.geom_type}"
        )
    if geom.is_empty:
        return Polygon()

    # Nothing to do: a valid input already covers exactly its own region.
    if geom.geom_type in _POLYGONAL and geom.is_valid:
        return geom

    for strategy in (_rebuild_from_rings, _via_make_valid, _via_buffer_zero):
        try:
            result = strategy(geom)
        except (GEOSException, ValueError):
            continue
        if result is not None:
            return result
    return Polygon()


def _rebuild_from_rings(geom):
    """Re-derive the enclosed region from the input's rings."""
    regions = []
    for poly in _polygons(geom):
        region = _polygon_region(poly)
        if region is not None:
            regions.append(region)
    if not regions:
        return Polygon()
    merged = regions[0] if len(regions) == 1 else unary_union(regions)
    return _as_polygonal(merged)


def _polygon_region(poly):
    """Region of a single (possibly invalid) polygon: shell minus holes."""
    shell = _ring_region(poly.exterior)
    if shell is None:
        return None
    holes = [
        hole
        for hole in (_ring_region(ring) for ring in poly.interiors)
        if hole is not None
    ]
    if holes:
        shell = shell.difference(holes[0] if len(holes) == 1 else unary_union(holes))
    if shell.is_empty:
        return None
    return shell


def _ring_region(ring):
    """Area enclosed by a single closed ring, which may cross itself.

    Returns ``None`` when the ring encloses nothing (collapsed or degenerate).
    """
    coords = list(ring.coords)
    if len(coords) < 4:
        return None

    # Simple rings bound exactly one face; skip the noding machinery.
    if ring.is_simple:
        candidate = Polygon(coords)
        if candidate.is_valid and not candidate.is_empty:
            return candidate

    faces = list(polygonize(_node(LineString(coords))))
    faces = [face for face in faces if not face.is_empty]
    if not faces:
        return None
    merged = faces[0] if len(faces) == 1 else unary_union(faces)
    return None if merged.is_empty else merged


def _node(line):
    """Split ``line`` at every intersection, including self-intersections."""
    noder = getattr(shapely, "node", None)
    if noder is not None:
        try:
            return _parts(noder(MultiLineString([line])))
        except GEOSException:
            pass
    return _parts(unary_union([line, line]))


def _parts(geom):
    """Flatten a geometry into a list of single-part geometries."""
    if geom is None or geom.is_empty:
        return []
    members = getattr(geom, "geoms", None)
    if members is None:
        return [geom]
    out = []
    for member in members:
        out.extend(_parts(member))
    return out


def _polygons(geom):
    """Every polygon contained in ``geom``, however deeply nested."""
    return [part for part in _parts(geom) if part.geom_type == "Polygon"]


def _as_polygonal(geom):
    """Coerce ``geom`` to a valid ``Polygon``/``MultiPolygon``, dropping any
    lower-dimensional debris."""
    polys = [poly for poly in _polygons(geom) if not poly.is_empty]
    if not polys:
        return Polygon()
    if len(polys) == 1 and polys[0].is_valid:
        return polys[0]
    merged = unary_union(polys)
    polys = [poly for poly in _polygons(merged) if not poly.is_empty]
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)


def _via_make_valid(geom):
    """Fallback: let GEOS repair the geometry, then keep the polygonal part."""
    return _as_polygonal(shapely.make_valid(geom))


def _via_buffer_zero(geom):
    """Last-resort fallback for inputs that defeat the overlay engine."""
    return _as_polygonal(geom.buffer(0))
```