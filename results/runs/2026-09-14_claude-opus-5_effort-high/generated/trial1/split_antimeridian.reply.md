```python
"""Split EPSG:4326 polygons that cross the antimeridian.

The only public entry point is :func:`split_antimeridian`.  Importing this
module has no side effects.

The approach is the standard one: longitudes are "unwrapped" so that the ring
becomes continuous in a plane where longitude is allowed to run outside
[-180, 180], the unwrapped polygon is clipped against the 360-degree-wide
strips that plane decomposes into, and every clipped piece is translated back
into [-180, 180].
"""

from __future__ import annotations

import math
from typing import Iterable, Iterator, List, Sequence, Tuple

from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_LON_MAX = 180.0
_PERIOD = 360.0

# A longitude step of (almost) exactly one full period only happens between a
# vertex at exactly -180 and one at exactly +180, as in a whole-world box.  In
# plate carree that describes a segment spanning every longitude, not a jump
# across the antimeridian, so such steps are left alone.
_FULL_PERIOD_TOL = 1e-9

# Clipped edges should land exactly on +/-180; GEOS puts them there already,
# but the translation back can leave a float's breadth of error behind.
_SNAP_TOL = 1e-9

Coord = Tuple[float, float]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` in EPSG:4326 with
        longitudes in [-180, 180].  It crosses the antimeridian when
        consecutive vertices jump between values near +180 and near -180.

    Returns
    -------
    list of Polygon
        Valid polygons that together cover exactly the region ``polygon``
        covers, none of which crosses the antimeridian (they may touch it
        along an edge).  A polygon that does not cross the antimeridian is
        returned unchanged as the single element of the list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a :class:`~shapely.geometry.Polygon`.
    ValueError
        If a ring winds all the way around the globe, which is how a polygon
        enclosing a pole shows up in these coordinates.  Such a polygon has no
        unambiguous lon/lat representation and cannot be split.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(
            "expected a shapely Polygon, got {}".format(type(polygon).__name__)
        )
    if polygon.is_empty:
        return [polygon]

    shell = _unwrap_ring(polygon.exterior.coords)
    shell_area = _repaired(Polygon(shell))
    holes = [
        _align_hole(_unwrap_ring(ring.coords), shell_area)
        for ring in polygon.interiors
    ]

    unwrapped = Polygon(shell, holes)
    xmin, ymin, xmax, ymax = unwrapped.bounds
    if xmin >= -_LON_MAX and xmax <= _LON_MAX:
        return [polygon]

    # Strip k spans [-180 + 360k, 180 + 360k]; keep those that overlap the
    # unwrapped polygon with non-zero width.
    k_min = int(math.floor((xmin - _LON_MAX) / _PERIOD)) + 1
    k_max = int(math.ceil((xmax + _LON_MAX) / _PERIOD)) - 1

    clipable = _repaired(unwrapped)
    pieces: List[Polygon] = []
    for k in range(k_min, k_max + 1):
        offset = k * _PERIOD
        strip = box(-_LON_MAX + offset, ymin - 1.0, _LON_MAX + offset, ymax + 1.0)
        clipped = clipable.intersection(strip)
        if clipped.is_empty:
            continue
        pieces.extend(_polygons(translate(clipped, xoff=-offset)))

    # A polygon whose unwrapped span exceeds a full period wraps over itself;
    # the translated pieces then overlap and have to be merged.
    if len(pieces) > 1 and (xmax - xmin) > _PERIOD + _SNAP_TOL:
        pieces = list(_polygons(unary_union(pieces)))

    result: List[Polygon] = []
    for piece in pieces:
        snapped = _repaired(_snap_to_antimeridian(piece))
        result.extend(_polygons(snapped))

    result.sort(key=lambda p: p.bounds)
    return result


def _unwrap_ring(coords: Iterable[Sequence[float]]) -> List[Coord]:
    """Return the ring's vertices with antimeridian jumps undone."""
    points = [(float(c[0]), float(c[1])) for c in coords]
    if not points:
        return []

    unwrapped = [points[0]]
    offset = 0.0
    previous = points[0][0]
    for lon, lat in points[1:]:
        delta = lon - previous
        if abs(delta) > _LON_MAX and abs(delta) < _PERIOD - _FULL_PERIOD_TOL:
            offset -= math.copysign(_PERIOD, delta)
        unwrapped.append((lon + offset, lat))
        previous = lon

    if abs(offset) > _FULL_PERIOD_TOL:
        raise ValueError(
            "ring winds around the globe (net longitude change of "
            "{:g} degrees); polygons enclosing a pole cannot be split at the "
            "antimeridian".format(offset)
        )
    return unwrapped


def _align_hole(hole: List[Coord], shell_area: BaseGeometry) -> List[Coord]:
    """Shift an unwrapped hole by whole periods so it sits inside the shell.

    Each ring is unwrapped starting from its own first vertex, so a hole can
    come out a full period away from the shell that contains it.
    """
    if not hole:
        return hole

    shell_lo, _, shell_hi, _ = shell_area.bounds
    shell_mid = 0.5 * (shell_lo + shell_hi)
    lons = [x for x, _ in hole]
    lo, hi = min(lons), max(lons)
    mid = 0.5 * (lo + hi)

    k_min = int(math.floor((shell_lo - hi) / _PERIOD))
    k_max = int(math.ceil((shell_hi - lo) / _PERIOD))

    best: List[Coord] = hole
    best_score = (-1.0, -math.inf)
    for k in range(k_min, k_max + 1):
        offset = k * _PERIOD
        shifted = [(x + offset, y) for x, y in hole]
        overlap = shell_area.intersection(_repaired(Polygon(shifted))).area
        score = (overlap, -abs(mid + offset - shell_mid))
        if score > best_score:
            best_score, best = score, shifted
    return best


def _repaired(geometry: BaseGeometry) -> BaseGeometry:
    """Return a valid equivalent of ``geometry``."""
    if geometry.is_valid:
        return geometry
    return make_valid(geometry)


def _polygons(geometry: BaseGeometry) -> Iterator[Polygon]:
    """Yield the non-degenerate polygons contained in ``geometry``."""
    if geometry.is_empty:
        return
    if isinstance(geometry, Polygon):
        if geometry.area > 0.0:
            yield geometry
    elif isinstance(geometry, (MultiPolygon,)) or hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygons(part)


def _snap_to_antimeridian(polygon: Polygon) -> Polygon:
    """Pull coordinates onto +/-180 when rounding left them just beside it."""
    return Polygon(
        _snap_ring(polygon.exterior.coords),
        [_snap_ring(ring.coords) for ring in polygon.interiors],
    )


def _snap_ring(coords: Iterable[Sequence[float]]) -> List[Coord]:
    return [(_snap_lon(float(c[0])), float(c[1])) for c in coords]


def _snap_lon(lon: float) -> float:
    for edge in (-_LON_MAX, _LON_MAX):
        if abs(lon - edge) <= _SNAP_TOL:
            return edge
    # Clipping guarantees the value is already inside the strip; this only
    # absorbs rounding error from the translation.
    return min(max(lon, -_LON_MAX), _LON_MAX)
```