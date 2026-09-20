"""Repair invalid shapely polygons without gaining or losing covered area.

:func:`fix_geometry` accepts a shapely :class:`~shapely.Polygon` or
:class:`~shapely.MultiPolygon` that may be invalid -- self-intersecting rings,
overlapping parts, and so on -- and returns a *valid* polygonal geometry
covering exactly the region enclosed by the input's rings.

The repair is structural: every ring keeps its declared role, and no ring's
enclosed area is ever cancelled out.

* The region of a single ring is the union of every bounded face of the planar
  arrangement of that ring's linework -- that is, every point that cannot be
  reached from infinity without crossing the ring.  Self-intersections
  therefore never subtract area (as ``buffer(0)`` and the even-odd rule do),
  and nothing outside the ring's own linework is ever invented.
* A polygon's region is its shell's region minus the regions of its holes.
* A multi-polygon's region is the union of its members' regions.

Valid input is returned untouched, so it trivially still covers the same
region.
"""

from __future__ import annotations

from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid

__all__ = ["fix_geometry"]


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the same region as ``geom``.

    Parameters
    ----------
    geom : shapely.Polygon or shapely.MultiPolygon
        Geometry to repair.  It may be invalid.

    Returns
    -------
    shapely.Polygon or shapely.MultiPolygon
        A valid geometry covering every location enclosed by ``geom``'s rings
        and nothing more.  An empty ``Polygon`` is returned when the input
        encloses no area at all.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or a ``MultiPolygon``.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(
            "fix_geometry() expects a shapely Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )
    if geom.is_empty or geom.is_valid:
        return geom

    members = geom.geoms if isinstance(geom, MultiPolygon) else (geom,)
    parts = [fixed for fixed in map(_fix_polygon, members) if not fixed.is_empty]
    if not parts:
        return Polygon()

    result = _polygonal(unary_union(parts))
    if not result.is_valid:  # belt and braces; GEOS output should already be valid
        result = _polygonal(make_valid(result))
    return result


def _fix_polygon(poly):
    """Repair a single polygon: its shell's region minus its holes' regions."""
    if poly.is_empty:
        return Polygon()
    if poly.is_valid:
        return poly

    shell = _ring_region(poly.exterior)
    if shell.is_empty:
        return Polygon()

    holes = [hole for hole in map(_ring_region, poly.interiors) if not hole.is_empty]
    if holes:
        shell = shell.difference(unary_union(holes))
    return _polygonal(shell)


def _ring_region(ring):
    """Return the region enclosed by one ring, self-intersections included."""
    if ring.is_empty or len(ring.coords) < 4:
        return Polygon()

    line = LineString(ring.coords)
    try:
        # A unary union of the linework splits the ring at its own crossings,
        # and polygonizing that noded linework yields every face it bounds:
        # both the faces an even-odd fix would cancel out and the ones it would
        # turn into holes, which the union below fills back in.
        noded = unary_union(line)
        faces = list(polygonize(list(getattr(noded, "geoms", (noded,)))))
        region = unary_union(faces) if faces else Polygon()
    except GEOSException:
        region = make_valid(Polygon(ring))
    return _polygonal(region)


def _polygonal(geom):
    """Coerce a geometry to a ``Polygon``/``MultiPolygon``, dropping collapsed parts."""
    polys = [part for part in _flatten(geom) if isinstance(part, Polygon)]
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)


def _flatten(geom):
    """Yield the non-empty, non-collection components of ``geom``."""
    if geom is None or geom.is_empty:
        return
    parts = getattr(geom, "geoms", None)
    if parts is None:
        yield geom
    else:
        for part in parts:
            yield from _flatten(part)