```python
"""Split shapely polygons that cross the antimeridian (the ±180° meridian).

The single public function, :func:`split_antimeridian`, takes an EPSG:4326
polygon whose longitudes lie in [-180, 180] and whose ring may "jump" between
values near +180 and values near -180 when it crosses the antimeridian. It
returns a list of valid polygons that together cover the same region and none
of which crosses the antimeridian.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from shapely import make_valid
from shapely.affinity import translate
from shapely.geometry import LinearRing, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

_HALF_TURN = 180.0
_FULL_TURN = 360.0
_MIN_AREA = 1e-12


def _has_jump(coords: Sequence[Tuple[float, ...]]) -> bool:
    """True if consecutive vertices differ in longitude by more than 180°."""
    for (lon_a, *_), (lon_b, *_) in zip(coords, coords[1:]):
        if abs(lon_b - lon_a) > _HALF_TURN:
            return True
    return False


def _unwrap_ring(coords: Sequence[Tuple[float, ...]]) -> List[Tuple[float, float]]:
    """Return ring coordinates with longitudes made continuous.

    Each vertex is shifted by a multiple of 360° so that no consecutive pair
    differs by more than 180° in longitude. The first vertex is left as is.
    """
    if not coords:
        return []
    out: List[Tuple[float, float]] = [(float(coords[0][0]), float(coords[0][1]))]
    prev = out[0][0]
    for lon, lat, *_ in coords[1:]:
        lon = float(lon)
        while lon - prev > _HALF_TURN:
            lon -= _FULL_TURN
        while lon - prev < -_HALF_TURN:
            lon += _FULL_TURN
        out.append((lon, float(lat)))
        prev = lon
    return out


def _align_to(ring: List[Tuple[float, float]], target_mid: float) -> List[Tuple[float, float]]:
    """Shift a whole ring by a multiple of 360° so its midpoint is nearest target_mid."""
    lons = [lon for lon, _ in ring]
    mid = (min(lons) + max(lons)) / 2.0
    shift = round((target_mid - mid) / _FULL_TURN) * _FULL_TURN
    if shift == 0:
        return ring
    return [(lon + shift, lat) for lon, lat in ring]


def _polygons_of(geom: BaseGeometry) -> List[Polygon]:
    """Flatten a geometry into its polygonal components with positive area."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > _MIN_AREA else []
    if isinstance(geom, MultiPolygon):
        return [p for p in geom.geoms if p.area > _MIN_AREA]
    if hasattr(geom, "geoms"):
        result: List[Polygon] = []
        for part in geom.geoms:
            result.extend(_polygons_of(part))
        return result
    return []


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split a lon/lat polygon along the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in EPSG:4326 with longitudes in [-180, 180].
        If the ring crosses the antimeridian, consecutive vertices jump between
        values near +180 and values near -180.

    Returns
    -------
    list of Polygon
        Valid polygons covering exactly the same area, none of which crosses
        the antimeridian. If the input does not cross, ``[polygon]`` is
        returned with the original object unchanged.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    rings = [list(polygon.exterior.coords)] + [list(r.coords) for r in polygon.interiors]
    if not any(_has_jump(r) for r in rings):
        return [polygon]

    # Unwrap into a continuous longitude space where the ring no longer jumps.
    exterior = _unwrap_ring(rings[0])
    ext_lons = [lon for lon, _ in exterior]
    ext_mid = (min(ext_lons) + max(ext_lons)) / 2.0
    interiors = [_align_to(_unwrap_ring(r), ext_mid) for r in rings[1:]]

    unwrapped: BaseGeometry = Polygon(LinearRing(exterior), [LinearRing(r) for r in interiors])
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)

    minx, _, maxx, _ = unwrapped.bounds
    # World copy k spans longitudes [-180 + 360k, 180 + 360k].
    k_lo = math.floor((minx + _HALF_TURN) / _FULL_TURN)
    k_hi = math.floor((maxx + _HALF_TURN) / _FULL_TURN)
    if maxx == -_HALF_TURN + _FULL_TURN * k_hi:
        # Touching the boundary from the left only; no area in copy k_hi.
        k_hi -= 1

    pieces: List[Polygon] = []
    for k in range(k_lo, k_hi + 1):
        west = -_HALF_TURN + _FULL_TURN * k
        east = _HALF_TURN + _FULL_TURN * k
        clipped = unwrapped.intersection(box(west, -90.0, east, 90.0))
        for part in _polygons_of(clipped):
            shifted = translate(part, xoff=-_FULL_TURN * k) if k else part
            if not shifted.is_valid:
                shifted = make_valid(shifted)
            pieces.extend(_polygons_of(shifted))

    return pieces
```