"""Split EPSG:4326 polygons that cross the antimeridian.

A polygon given as longitude/latitude pairs with longitudes wrapped into
[-180, 180] is ambiguous at the antimeridian: an edge from +179 to -179 is a
two-degree hop across the dateline, but as plain planar coordinates it reads as
a 358-degree sweep back across the whole map.  The convention used here is the
usual one -- a longitude step of more than 180 degrees between consecutive
vertices is a wrap, not a real edge.

The split works by unwrapping each ring into a continuous longitude space (so a
polygon over the dateline occupies, say, [170, 190]), clipping that against the
360-degree-wide windows centred on every multiple of 360, and shifting each
clipped piece back into [-180, 180].

Importing this module has no side effects.
"""

from __future__ import annotations

import math

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_HALF_PERIOD = 180.0


def split_antimeridian(polygon):
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in EPSG:4326 with longitudes in [-180, 180].
        Consecutive vertices that jump between values near +180 and values
        near -180 are interpreted as crossing the antimeridian.

    Returns
    -------
    list of Polygon
        Valid polygons whose union covers exactly the region ``polygon``
        describes on the sphere, none of which crosses the antimeridian; they
        may touch it along their boundary.  A polygon that does not cross the
        antimeridian is returned unchanged as a single-element list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If a ring winds all the way around the Earth (a polygon enclosing a
        pole), which this representation cannot express.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")

    if polygon.is_empty or not _crosses_antimeridian(polygon):
        return [polygon]

    unwrapped = _unwrap_polygon(polygon)

    # Validity is checked *after* unwrapping, never before: a polygon spanning
    # the dateline is routinely self-intersecting when read as planar
    # coordinates, and unwrapping is exactly what repairs it.
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)

    return _clip_to_lon_windows(unwrapped)


def _rings(polygon):
    yield polygon.exterior
    yield from polygon.interiors


def _ring_array(ring):
    """Ring coordinates as an ``(n, 2)`` or ``(n, 3)`` float array."""
    coords = np.asarray(ring.coords, dtype=float)
    return coords.reshape(0, 2) if coords.size == 0 else coords


def _crosses_antimeridian(polygon):
    for ring in _rings(polygon):
        lons = _ring_array(ring)[:, 0]
        if lons.size > 1 and np.any(np.abs(np.diff(lons)) > _HALF_PERIOD):
            return True
    return False


def _unwrap_lons(lons):
    """Add multiples of 360 so consecutive longitudes differ by at most 180."""
    if lons.size < 2:
        return lons.copy()
    # np.round is half-to-even, so a step of exactly +/-180 rounds to 0 and is
    # left alone -- matching the `> 180` test used to detect a crossing.
    corrections = -_PERIOD * np.round(np.diff(lons) / _PERIOD)
    unwrapped = lons.copy()
    unwrapped[1:] += np.cumsum(corrections)
    return unwrapped


def _unwrap_ring(ring):
    coords = _ring_array(ring).copy()
    lons = _unwrap_lons(coords[:, 0])
    if lons.size and lons[-1] != lons[0]:
        raise ValueError(
            "ring winds around the Earth in longitude; polygons enclosing a "
            "pole cannot be split at the antimeridian"
        )
    coords[:, 0] = lons
    return coords


def _unwrap_polygon(polygon):
    shell = _unwrap_ring(polygon.exterior)
    shell_centre = 0.5 * (shell[:, 0].min() + shell[:, 0].max())

    holes = []
    for interior in polygon.interiors:
        hole = _unwrap_ring(interior)
        if hole.size == 0:
            continue
        # Each ring unwraps relative to its own first vertex, so a hole can land
        # a full period away from the shell that contains it; slide it back.
        hole_centre = 0.5 * (hole[:, 0].min() + hole[:, 0].max())
        hole[:, 0] += _PERIOD * round((shell_centre - hole_centre) / _PERIOD)
        holes.append(hole)

    return Polygon(shell, holes)


def _clip_to_lon_windows(geom):
    """Cut ``geom`` along every 180 + 360k meridian and fold the pieces home."""
    minx, miny, maxx, maxy = geom.bounds
    first = math.floor((minx + _HALF_PERIOD) / _PERIOD)
    last = math.floor((maxx + _HALF_PERIOD) / _PERIOD)

    pieces = []
    for k in range(first, last + 1):
        offset = _PERIOD * k
        window = box(offset - _HALF_PERIOD, miny - 1.0, offset + _HALF_PERIOD, maxy + 1.0)
        clipped = geom.intersection(window)
        if clipped.is_empty:
            continue
        # Clipped vertices sit exactly on the window edge, so shifting by a
        # whole period lands them exactly on -180 or +180.
        pieces.extend(_polygons(translate(clipped, xoff=-offset)))
    return pieces


def _polygons(geom):
    """Polygonal parts of ``geom`` with area, dropping lines, points, slivers."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > 0.0 else []
    parts = []
    for part in getattr(geom, "geoms", ()):
        parts.extend(_polygons(part))
    return parts