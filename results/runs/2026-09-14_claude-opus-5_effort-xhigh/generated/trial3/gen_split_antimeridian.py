"""Antimeridian-safe splitting of EPSG:4326 (lon/lat) polygons.

Importing this module has no side effects: it only defines constants, a few
private helpers and :func:`split_antimeridian`.

The approach is the classic one: longitudes are first *unwrapped* so that the
ring becomes continuous (a step of more than 180 degrees between consecutive
vertices is interpreted as an antimeridian jump and undone by adding or
subtracting a full 360 degree period).  The continuous polygon is then clipped
against the 360 degree wide longitude bands ``[-180 + 360k, 180 + 360k]`` and
every piece is translated back into ``[-180, 180]``.
"""

from __future__ import annotations

import math
from typing import Iterable, Iterator, List, Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_PERIOD = 360.0  # full longitude range
_HALF = 180.0  # longitude of the antimeridian
_TOL = 1e-9

_Ring = List[Tuple[float, float]]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` so that no returned part crosses the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` whose coordinates are
        longitude/latitude in EPSG:4326, with longitudes in ``[-180, 180]``.
        The polygon may cross the antimeridian, in which case consecutive
        vertices jump between values near ``+180`` and values near ``-180``.

    Returns
    -------
    list of Polygon
        Polygons that together cover exactly the same region of the Earth and
        none of which crosses the antimeridian (touching it along the
        ``+180`` / ``-180`` edge is allowed).  A polygon that does not cross
        the antimeridian is returned unchanged as a single-element list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If a ring winds around the Earth more than once, or if a hole encircles
        a pole while the exterior ring does not (such input cannot describe a
        single region on the sphere).

    Notes
    -----
    * A step of exactly 360 degrees between consecutive vertices (i.e. a vertex
      at ``-180`` followed by one at ``+180`` or vice versa) is *not* treated
      as a jump, so a polygon spanning the whole world is preserved.
    * A ring whose longitudes drift by a full period encircles a pole.  Which
      pole is enclosed is determined from the traversal direction using the
      right-hand rule (RFC 7946): an eastward exterior ring encloses the north
      pole, a westward one the south pole.  Such a polygon is closed off along
      the pole before being split.
    * Z values are dropped from polygons that actually get split.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(
            "split_antimeridian() expects a shapely Polygon, got "
            f"{type(polygon).__name__}"
        )
    if polygon.is_empty:
        return [polygon]

    shell, shell_drift, shifted = _unwrap(polygon.exterior.coords)
    _check_drift(shell_drift, "exterior ring")

    shell_lons = [x for x, _ in shell]
    center = 0.5 * (min(shell_lons) + max(shell_lons))

    holes: _Ring = []
    hole_drifts: List[float] = []
    for interior in polygon.interiors:
        ring, drift, ring_shifted = _unwrap(interior.coords)
        _check_drift(drift, "interior ring")
        ring, moved = _recenter(ring, center)
        shifted = shifted or ring_shifted or moved
        holes.append(ring)
        hole_drifts.append(drift)

    encircles_pole = _winds(shell_drift) or any(_winds(d) for d in hole_drifts)

    if not encircles_pole and not shifted:
        if min(shell_lons) >= -_HALF and max(shell_lons) <= _HALF:
            # Nothing was reinterpreted and the polygon already lives inside a
            # single band: hand back the caller's own geometry untouched.
            return [polygon]

    if encircles_pole:
        pole = _pole_latitude(shell_drift, hole_drifts)
        if _winds(shell_drift):
            shell = _close_over_pole(shell, pole)
        holes = [
            _close_over_pole(ring, pole) if _winds(drift) else ring
            for ring, drift in zip(holes, hole_drifts)
        ]

    unwrapped: BaseGeometry = Polygon(shell, holes)
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)
    if unwrapped.is_empty:
        return []

    return _clip_to_bands(unwrapped)


def _unwrap(coords: Iterable[Tuple[float, ...]]) -> Tuple[_Ring, float, bool]:
    """Undo antimeridian jumps in one ring.

    Returns the unwrapped ring, its longitude drift (``last - first``, a
    multiple of 360) and whether any vertex had to be moved.
    """
    ring: _Ring = []
    offset = 0.0
    shifted = False
    previous = None
    for coord in coords:
        x, y = float(coord[0]), float(coord[1])
        if previous is not None:
            step = x - previous
            # A |step| of exactly one period means the vertices sit on the same
            # meridian (-180 and +180), which is not a jump.
            if _HALF < abs(step) < _PERIOD:
                offset -= math.copysign(_PERIOD, step)
        previous = x
        if offset:
            shifted = True
        ring.append((x + offset, y))
    drift = ring[-1][0] - ring[0][0]
    return ring, drift, shifted


def _winds(drift: float) -> bool:
    """True if a ring's longitudes drift by a full period, i.e. it circles a pole."""
    return abs(drift) > _TOL


def _check_drift(drift: float, what: str) -> None:
    if _winds(drift) and abs(abs(drift) - _PERIOD) > _TOL:
        raise ValueError(f"{what} winds around the Earth more than once")


def _recenter(ring: _Ring, center: float) -> Tuple[_Ring, bool]:
    """Shift a hole by whole periods so it sits next to the unwrapped shell."""
    lons = [x for x, _ in ring]
    k = round((center - 0.5 * (min(lons) + max(lons))) / _PERIOD)
    if not k:
        return ring, False
    return [(x + k * _PERIOD, y) for x, y in ring], True


def _pole_latitude(shell_drift: float, hole_drifts: List[float]) -> float:
    if not _winds(shell_drift):
        raise ValueError(
            "a hole encircles a pole but the exterior ring does not; "
            "the polygon does not describe a single region on the sphere"
        )
    return 90.0 if shell_drift > 0 else -90.0


def _close_over_pole(ring: _Ring, pole_lat: float) -> _Ring:
    """Close a pole-encircling ring by running it along the pole."""
    return ring + [(ring[-1][0], pole_lat), (ring[0][0], pole_lat), ring[0]]


def _clip_to_bands(geom: BaseGeometry) -> List[Polygon]:
    """Cut ``geom`` along every multiple of 180 and fold the pieces back home."""
    minx, miny, maxx, maxy = geom.bounds
    k_lo = math.floor((minx + _HALF) / _PERIOD)
    k_hi = math.floor((maxx + _HALF) / _PERIOD)
    # A geometry ending exactly on a band edge does not reach into the next band.
    if k_hi > k_lo and maxx <= -_HALF + k_hi * _PERIOD:
        k_hi -= 1

    if k_lo == k_hi:
        xoff = -k_lo * _PERIOD
        return [translate(part, xoff=xoff) if xoff else part for part in _polygons(geom)]

    pieces: List[Polygon] = []
    for k in range(k_lo, k_hi + 1):
        band = box(-_HALF + k * _PERIOD, miny, _HALF + k * _PERIOD, maxy)
        clipped = geom.intersection(band)
        if clipped.is_empty:
            continue
        xoff = -k * _PERIOD
        for part in _polygons(clipped):
            pieces.append(translate(part, xoff=xoff) if xoff else part)
    return pieces


def _polygons(geom: BaseGeometry) -> Iterator[Polygon]:
    """Yield the non-degenerate polygonal parts of ``geom``."""
    if isinstance(geom, Polygon):
        if not geom.is_empty and geom.area > 0.0:
            yield geom
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _polygons(part)