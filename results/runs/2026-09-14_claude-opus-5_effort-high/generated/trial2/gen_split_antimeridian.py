"""Antimeridian-safe splitting of EPSG:4326 polygons.

A polygon whose vertices are stored as longitude/latitude in [-180, 180] can
describe a region that straddles the antimeridian; when it does, consecutive
vertices of a ring jump by more than 180 degrees of longitude.  Such a polygon
is not usable as-is: interpreted in the plane it wraps the wrong way around the
globe.  :func:`split_antimeridian` re-reads the rings in a continuous
("unwrapped") longitude frame and cuts the result at every multiple of 360
degrees, returning pieces that live entirely inside [-180, 180].

Importing this module has no side effects.

Known limitation: a ring that encircles a geographic pole accumulates a full
360 degrees of longitude when unwrapped, so its first and last vertex no longer
coincide.  Such input is not handled specially and the result is not meaningful;
pole-enclosing geometry needs a projected treatment instead.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.validation import make_valid

__all__ = ["split_antimeridian", "crosses_antimeridian"]

_PERIOD = 360.0
_HALF = 180.0
#: Latitude padding for the clipping windows, so they never graze the input.
_LAT_PAD = 1.0

_XY = Tuple[float, float]


def _ring_coords(ring) -> List[_XY]:
    """Ring vertices as 2D tuples; any z ordinate is dropped."""
    return [(float(p[0]), float(p[1])) for p in ring.coords]


def _unwrap(points: List[_XY]) -> List[_XY]:
    """Remove +/-360 discontinuities, keeping each step shorter than 180.

    A step of exactly 180 degrees is ambiguous and is left untouched, which
    matches the strict comparison used by :func:`crosses_antimeridian`.
    """
    out: List[_XY] = []
    prev = None
    for x, y in points:
        if prev is not None:
            x -= _PERIOD * round((x - prev) / _PERIOD)
        out.append((x, y))
        prev = x
    return out


def _span_mid(points: List[_XY]) -> float:
    xs = [x for x, _ in points]
    return 0.5 * (min(xs) + max(xs))


def _shift(points: List[_XY], dx: float) -> List[_XY]:
    if dx == 0.0:
        return list(points)
    return [(x + dx, y) for x, y in points]


def crosses_antimeridian(polygon: Polygon) -> bool:
    """True if any ring of *polygon* has an edge jumping more than 180 degrees."""
    if polygon.is_empty:
        return False
    for ring in (polygon.exterior, *polygon.interiors):
        coords = _ring_coords(ring)
        for (x0, _), (x1, _) in zip(coords, coords[1:]):
            if abs(x1 - x0) > _HALF:
                return True
    return False


def _collect_polygons(geom, out: List[Polygon], fix: bool = True) -> None:
    """Flatten *geom* into positive-area, valid polygons appended to *out*."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        if geom.area <= 0.0:
            return
        if geom.is_valid:
            out.append(geom)
        elif fix:
            _collect_polygons(make_valid(geom), out, fix=False)
        return
    for part in getattr(geom, "geoms", ()):
        _collect_polygons(part, out, fix=fix)


def _clamp_to_domain(polygon: Polygon) -> Polygon:
    """Pull rounding-error excursions past +/-180 back onto the boundary."""
    xmin, _, xmax, _ = polygon.bounds
    if xmin >= -_HALF and xmax <= _HALF:
        return polygon

    def fix(points: List[_XY]) -> List[_XY]:
        return [(min(_HALF, max(-_HALF, x)), y) for x, y in points]

    clamped = Polygon(
        fix(_ring_coords(polygon.exterior)),
        [fix(_ring_coords(ring)) for ring in polygon.interiors],
    )
    return clamped if clamped.is_valid and not clamped.is_empty else polygon


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split *polygon* at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` in EPSG:4326 with
        longitudes in [-180, 180].

    Returns
    -------
    list of Polygon
        Valid polygons that together cover exactly the region described by
        *polygon*, none of which crosses the antimeridian (they may touch it
        along an edge).  A polygon that does not cross the antimeridian is
        returned unchanged as the only element.  Zero-area slivers produced by
        the cut are discarded.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty or not crosses_antimeridian(polygon):
        return [polygon]

    exterior = _unwrap(_ring_coords(polygon.exterior))
    # Holes are unwrapped on their own, then translated by whole periods into
    # the frame the exterior ended up in.
    reference = _span_mid(exterior)
    interiors: List[List[_XY]] = []
    for ring in polygon.interiors:
        points = _unwrap(_ring_coords(ring))
        k = round((reference - _span_mid(points)) / _PERIOD)
        interiors.append(_shift(points, k * _PERIOD))

    unwrapped = Polygon(exterior, interiors)
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)

    xs = [x for x, _ in exterior]
    ys = [y for _, y in exterior]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    # Band k is the longitude window [360k - 180, 360k + 180]; band 0 is the
    # standard domain.  Cover every band the unwrapped polygon reaches into.
    k_lo = math.floor((xmin + _HALF) / _PERIOD)
    k_hi = math.floor((xmax + _HALF) / _PERIOD)
    if k_hi > k_lo and (xmax + _HALF) == k_hi * _PERIOD:
        k_hi -= 1  # xmax sits exactly on a band edge: the next band is empty

    pieces: List[Polygon] = []
    for k in range(k_lo, k_hi + 1):
        center = _PERIOD * k
        window = box(center - _HALF, ymin - _LAT_PAD, center + _HALF, ymax + _LAT_PAD)
        clipped: List[Polygon] = []
        _collect_polygons(unwrapped.intersection(window), clipped)
        for part in clipped:
            pieces.append(_clamp_to_domain(translate(part, xoff=-center)))

    if not pieces:
        return [polygon]

    pieces.sort(key=lambda geom: geom.bounds)
    return pieces