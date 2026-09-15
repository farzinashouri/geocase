```python
"""Split shapely polygons that cross the antimeridian (the 180th meridian).

The module is side-effect free on import: it only defines constants and
functions.

The single public entry point is :func:`split_antimeridian`.

Method
------
A polygon is considered to cross the antimeridian when two consecutive
vertices of one of its rings differ in longitude by more than 180 degrees:
on a sphere the short way between such vertices runs across the
antimeridian rather than across the whole globe.

The rings are therefore "unwrapped": walking along a ring, whenever such a
jump occurs a multiple of 360 degrees is added to all subsequent vertices so
that the ring becomes continuous in an unbounded longitude space.  The
unwrapped polygon is then clipped against the 360-degree-wide strips
``[360k - 180, 360k + 180]`` it overlaps, and every clipped piece is
translated back by ``-360k`` into ``[-180, 180]``.  The pieces cover exactly
the region of the original polygon and each of them lies inside one strip, so
none of them crosses the antimeridian; they may only touch it along their
boundary.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_LON_MAX = 180.0
# Tolerance used when snapping clipped coordinates back onto the strip edges
# and when deciding whether an unwrapped ring closes onto itself.
_EPS = 1e-9

Coords = Sequence[Tuple[float, float]]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in EPSG:4326 with longitudes in [-180, 180].

    Returns
    -------
    list of Polygon
        Polygons whose union covers exactly the same region of the Earth as
        ``polygon`` and none of which crosses the antimeridian (they may
        touch it with their boundary).  A polygon that does not cross the
        antimeridian is returned unchanged as a single-element list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If the polygon encircles a pole.  Such a polygon cannot be described
        by longitude/latitude rings alone once it is cut, so the caller has
        to decide how to close it along the pole.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    exterior = _unwrap(polygon.exterior.coords)
    if not _closes(exterior):
        raise ValueError(
            "polygon encircles a pole; it cannot be split at the antimeridian "
            "without adding vertices along the pole"
        )

    interiors = []
    for ring in polygon.interiors:
        interior = _unwrap(ring.coords)
        if not _closes(interior):
            raise ValueError(
                "polygon has a hole encircling a pole; it cannot be split at "
                "the antimeridian without adding vertices along the pole"
            )
        interiors.append(_align(interior, exterior))

    lon_min = min(x for x, _ in exterior)
    lon_max = max(x for x, _ in exterior)
    if lon_max - lon_min <= _PERIOD and _strip_index(lon_min) == _strip_index(lon_max):
        # Every vertex lives in a single strip: no crossing at all.
        return [polygon]

    unwrapped = make_valid(Polygon(exterior, interiors))
    lat_min = min(y for _, y in exterior)
    lat_max = max(y for _, y in exterior)
    # Pad the clipping box in latitude so the strip edges are the only cuts.
    lat_lo, lat_hi = lat_min - 1.0, lat_max + 1.0

    pieces: List[Polygon] = []
    for k in range(_strip_index(lon_min), _strip_index(lon_max) + 1):
        strip = box(k * _PERIOD - _LON_MAX, lat_lo, k * _PERIOD + _LON_MAX, lat_hi)
        clipped = unwrapped.intersection(strip)
        if clipped.is_empty:
            continue
        shifted = translate(clipped, xoff=-k * _PERIOD)
        pieces.extend(_as_polygons(shifted))

    return [_clamp(piece) for piece in pieces]


def _unwrap(coords: Coords) -> List[Tuple[float, float]]:
    """Make a ring continuous in longitude by removing the +-180 wrap-around."""
    unwrapped: List[Tuple[float, float]] = []
    offset = 0.0
    previous_lon = None
    for lon, lat in ((float(c[0]), float(c[1])) for c in coords):
        if previous_lon is not None:
            delta = lon - previous_lon
            if delta > _LON_MAX:
                offset -= _PERIOD
            elif delta < -_LON_MAX:
                offset += _PERIOD
        unwrapped.append((lon + offset, lat))
        previous_lon = lon
    return unwrapped


def _closes(ring: Coords) -> bool:
    """True unless unwrapping left the ring open, i.e. it encircles a pole."""
    return abs(ring[0][0] - ring[-1][0]) < _EPS


def _align(
    interior: Sequence[Tuple[float, float]], exterior: Sequence[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Shift a hole by whole periods so it sits inside the unwrapped shell."""
    interior_mid = (
        min(x for x, _ in interior) + max(x for x, _ in interior)
    ) / 2.0
    exterior_mid = (
        min(x for x, _ in exterior) + max(x for x, _ in exterior)
    ) / 2.0
    shift = _PERIOD * round((exterior_mid - interior_mid) / _PERIOD)
    if shift == 0.0:
        return list(interior)
    return [(x + shift, y) for x, y in interior]


def _strip_index(lon: float) -> int:
    """Index ``k`` of the strip ``[360k - 180, 360k + 180]`` containing ``lon``."""
    return int(math.floor((lon + _LON_MAX) / _PERIOD))


def _as_polygons(geometry: BaseGeometry) -> Iterable[Polygon]:
    """Yield the non-degenerate polygonal parts of any geometry."""
    if geometry.is_empty:
        return
    if isinstance(geometry, Polygon):
        if geometry.area > 0.0:
            yield geometry if geometry.is_valid else None
        return
    if isinstance(geometry, MultiPolygon) or hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _as_polygons(part)


def _clamp(polygon: Polygon) -> Polygon:
    """Snap coordinates onto [-180, 180] to absorb clipping round-off."""

    def fix(coords: Coords) -> List[Tuple[float, float]]:
        return [(min(max(x, -_LON_MAX), _LON_MAX), y) for x, y in coords]

    clamped = Polygon(
        fix(polygon.exterior.coords), [fix(r.coords) for r in polygon.interiors]
    )
    if clamped.is_valid:
        return clamped
    repaired = make_valid(clamped)
    parts = [p for p in _as_polygons(repaired) if p is not None]
    if len(parts) == 1:
        return parts[0]
    return polygon
```