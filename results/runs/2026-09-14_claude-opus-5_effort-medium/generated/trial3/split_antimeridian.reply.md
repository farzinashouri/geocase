```python
"""Split EPSG:4326 polygons that cross the antimeridian.

The module exposes a single public function, :func:`split_antimeridian`,
which takes a shapely ``Polygon`` in geographic coordinates (longitude,
latitude, degrees, longitudes in ``[-180, 180]``) and returns a list of
polygons covering exactly the same region of the Earth's surface, none of
which spans the antimeridian.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

_JUMP = 180.0
_PERIOD = 360.0
# Tolerance used to snap coordinates back onto the +/-180 meridian after the
# floating-point round trip through the clipping boxes.
_SNAP_EPS = 1e-9


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` whose coordinates are longitude/latitude in
        EPSG:4326 with longitudes in ``[-180, 180]``. The polygon is assumed
        to cross the antimeridian wherever two consecutive vertices differ in
        longitude by more than 180 degrees.

    Returns
    -------
    list of Polygon
        One polygon per longitude band the input occupies. A polygon that
        does not cross the antimeridian is returned unchanged as a
        single-element list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If the polygon encircles a pole, which cannot be represented as a
        set of EPSG:4326 polygons without inventing edges along the poles.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")

    if polygon.is_empty:
        return [polygon]

    exterior = _ring_coords(polygon.exterior.coords)
    interiors = [_ring_coords(ring.coords) for ring in polygon.interiors]

    if not any(_crosses(ring) for ring in [exterior] + interiors):
        return [polygon]

    unwrapped_exterior = _unwrap(exterior)
    if not _closes(unwrapped_exterior):
        raise ValueError(
            "polygon appears to encircle a pole; it cannot be split at the "
            "antimeridian into plain EPSG:4326 polygons"
        )

    lons = [lon for lon, _ in unwrapped_exterior]
    ext_mid = 0.5 * (min(lons) + max(lons))

    unwrapped_interiors = []
    for ring in interiors:
        unwrapped = _unwrap(ring)
        if not _closes(unwrapped):
            raise ValueError(
                "polygon has a hole that encircles a pole; it cannot be split "
                "at the antimeridian into plain EPSG:4326 polygons"
            )
        unwrapped_interiors.append(_align(unwrapped, ext_mid))

    unwrapped_polygon = Polygon(unwrapped_exterior, unwrapped_interiors)
    if not unwrapped_polygon.is_valid:
        unwrapped_polygon = unwrapped_polygon.buffer(0)
    if unwrapped_polygon.is_empty:
        return []

    min_lon, min_lat, max_lon, max_lat = unwrapped_polygon.bounds
    # Pad the clip boxes vertically so that only the meridians ever cut.
    lat_lo, lat_hi = min_lat - 1.0, max_lat + 1.0

    pieces: List[Polygon] = []
    for k in range(_band(min_lon), _band(max_lon) + 1):
        clip = box(k * _PERIOD - _JUMP, lat_lo, k * _PERIOD + _JUMP, lat_hi)
        part = unwrapped_polygon.intersection(clip)
        if part.is_empty:
            continue
        part = translate(part, xoff=-k * _PERIOD)
        pieces.extend(_snap(p) for p in _polygons(part))

    return [p for p in pieces if not p.is_empty]


def _ring_coords(coords: Iterable[Sequence[float]]) -> List[Tuple[float, float]]:
    """Drop any z ordinate; only longitude and latitude matter here."""
    return [(float(c[0]), float(c[1])) for c in coords]


def _crosses(ring: Sequence[Tuple[float, float]]) -> bool:
    return any(
        abs(ring[i][0] - ring[i - 1][0]) > _JUMP for i in range(1, len(ring))
    )


def _unwrap(ring: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Make a ring's longitudes continuous by undoing the +/-180 wrap."""
    out: List[Tuple[float, float]] = []
    offset = 0.0
    prev_lon = None
    for lon, lat in ring:
        if prev_lon is not None:
            delta = lon - prev_lon
            if delta > _JUMP:
                offset -= _PERIOD
            elif delta < -_JUMP:
                offset += _PERIOD
        out.append((lon + offset, lat))
        prev_lon = lon
    return out


def _closes(ring: Sequence[Tuple[float, float]]) -> bool:
    """True when unwrapping brought the ring back to its starting longitude.

    A non-zero net winding means the ring goes all the way around the globe,
    i.e. it encloses a pole.
    """
    return abs(ring[-1][0] - ring[0][0]) < _JUMP


def _align(ring: List[Tuple[float, float]], ext_mid: float) -> List[Tuple[float, float]]:
    """Shift a hole by whole turns so it sits in the exterior's frame."""
    lons = [lon for lon, _ in ring]
    mid = 0.5 * (min(lons) + max(lons))
    shift = round((ext_mid - mid) / _PERIOD) * _PERIOD
    if shift == 0.0:
        return ring
    return [(lon + shift, lat) for lon, lat in ring]


def _band(lon: float) -> int:
    """Index of the 360-degree band containing ``lon``; band k is [360k-180, 360k+180]."""
    import math

    return int(math.floor((lon + _JUMP) / _PERIOD))


def _polygons(geometry: BaseGeometry) -> List[Polygon]:
    """Flatten an intersection result down to its polygonal parts."""
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if hasattr(geometry, "geoms"):
        out: List[Polygon] = []
        for part in geometry.geoms:
            out.extend(_polygons(part))
        return out
    return []


def _snap(polygon: Polygon) -> Polygon:
    """Pull coordinates that landed a hair outside [-180, 180] back onto it."""

    def fix(value: float) -> float:
        if value > _JUMP:
            return _JUMP if value - _JUMP < _SNAP_EPS else value
        if value < -_JUMP:
            return -_JUMP if -_JUMP - value < _SNAP_EPS else value
        return value

    shell = [(fix(x), y) for x, y in polygon.exterior.coords]
    holes = [[(fix(x), y) for x, y in ring.coords] for ring in polygon.interiors]
    snapped = Polygon(shell, holes)
    if not snapped.is_valid:
        snapped = snapped.buffer(0)
        if isinstance(snapped, Polygon):
            return snapped
        parts = _polygons(snapped)
        if parts:
            return max(parts, key=lambda p: p.area)
        return polygon
    return snapped
```