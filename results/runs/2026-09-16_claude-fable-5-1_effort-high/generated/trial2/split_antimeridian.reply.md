Here is the module.

```python
"""Split EPSG:4326 polygons that cross the antimeridian into non-crossing pieces.

The public entry point is :func:`split_antimeridian`.  A polygon whose
consecutive vertices jump between longitudes near +180 and near -180 is
first "unwrapped" into a continuous ring on an extended longitude axis
(e.g. 170 .. 190), then clipped against 360-degree-wide windows and each
piece is shifted back into [-180, 180].  The returned polygons together
cover exactly the same region as the input and only ever touch the
antimeridian along their boundary.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian", "crosses_antimeridian"]

_Coord = Tuple[float, float]

_LON_SPAN = 360.0
_HALF_SPAN = 180.0


def _ring_coords(ring) -> List[_Coord]:
    """Return the (lon, lat) vertices of a ring, dropping any Z values."""
    return [(float(c[0]), float(c[1])) for c in ring.coords]


def _has_jump(coords: Sequence[_Coord]) -> bool:
    """True if any consecutive pair of vertices jumps more than 180 degrees."""
    return any(abs(b[0] - a[0]) > _HALF_SPAN for a, b in zip(coords, coords[1:]))


def crosses_antimeridian(polygon: Polygon) -> bool:
    """Return True if any ring of ``polygon`` jumps across the antimeridian."""
    rings = [polygon.exterior, *polygon.interiors]
    return any(_has_jump(_ring_coords(r)) for r in rings)


def _unwrap(coords: Sequence[_Coord]) -> List[_Coord]:
    """Make longitudes continuous by adding/subtracting 360 after each jump."""
    out: List[_Coord] = [coords[0]]
    offset = 0.0
    for prev, cur in zip(coords, coords[1:]):
        delta = cur[0] - prev[0]
        if delta > _HALF_SPAN:
            offset -= _LON_SPAN
        elif delta < -_HALF_SPAN:
            offset += _LON_SPAN
        out.append((cur[0] + offset, cur[1]))
    return out


def _close_ring(coords: List[_Coord]) -> List[_Coord]:
    """Ensure an unwrapped ring closes on itself.

    If the ring winds once around the globe (it encloses a pole), the
    unwrapped last vertex sits 360 degrees away from the first.  In that
    case the ring is closed over the nearer pole so the enclosed cap is
    represented explicitly.
    """
    first, last = coords[0], coords[-1]
    gap = last[0] - first[0]
    if abs(gap) < 1e-9:
        return coords
    mean_lat = sum(lat for _, lat in coords) / len(coords)
    pole_lat = 90.0 if mean_lat >= 0.0 else -90.0
    return coords + [(last[0], pole_lat), (first[0], pole_lat), first]


def _mean_lon(coords: Sequence[_Coord]) -> float:
    return sum(lon for lon, _ in coords) / len(coords)


def _align_to(coords: List[_Coord], target_lon: float) -> List[_Coord]:
    """Shift a ring by a multiple of 360 so its mean longitude is nearest target."""
    k = round((target_lon - _mean_lon(coords)) / _LON_SPAN)
    if k == 0:
        return coords
    shift = k * _LON_SPAN
    return [(lon + shift, lat) for lon, lat in coords]


def _polygons_of(geom: BaseGeometry) -> List[Polygon]:
    """Extract all non-empty, positive-area polygons from any geometry."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > 0.0 else []
    if hasattr(geom, "geoms"):
        found: List[Polygon] = []
        for part in geom.geoms:
            found.extend(_polygons_of(part))
        return found
    return []


def _valid(geom: BaseGeometry) -> BaseGeometry:
    return geom if geom.is_valid else make_valid(geom)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
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
        If the polygon does not cross the antimeridian, ``[polygon]`` (the
        same object, unchanged).  Otherwise, a list of valid polygons that
        together cover exactly the same region and none of which crosses the
        antimeridian; pieces may share an edge along longitude +180 or -180.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty or not crosses_antimeridian(polygon):
        return [polygon]

    exterior = _close_ring(_unwrap(_ring_coords(polygon.exterior)))
    anchor = _mean_lon(exterior)
    interiors = [
        _align_to(_close_ring(_unwrap(_ring_coords(ring))), anchor)
        for ring in polygon.interiors
    ]

    unwrapped = _valid(Polygon(exterior, interiors))

    min_lon, _, max_lon, _ = unwrapped.bounds
    k_lo = math.floor((min_lon + _HALF_SPAN) / _LON_SPAN)
    k_hi = math.floor((max_lon + _HALF_SPAN) / _LON_SPAN)

    pieces: List[Polygon] = []
    for k in range(k_lo, k_hi + 1):
        shift = k * _LON_SPAN
        window = box(-_HALF_SPAN + shift, -90.0, _HALF_SPAN + shift, 90.0)
        clipped = unwrapped.intersection(window)
        if clipped.is_empty:
            continue
        if k != 0:
            clipped = translate(clipped, xoff=-shift)
        pieces.extend(_polygons_of(_valid(clipped)))

    return pieces
```