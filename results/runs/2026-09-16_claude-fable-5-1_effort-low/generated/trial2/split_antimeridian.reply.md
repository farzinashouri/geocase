```python
"""Split EPSG:4326 polygons that cross the antimeridian (lon = ±180).

The only public entry point is :func:`split_antimeridian`.
"""

from __future__ import annotations

from typing import List

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_JUMP_THRESHOLD = 180.0


def _ring_crosses(coords) -> bool:
    """True if consecutive vertices jump by more than 180 degrees of longitude."""
    lons = [c[0] for c in coords]
    for a, b in zip(lons, lons[1:]):
        if abs(b - a) > _JUMP_THRESHOLD:
            return True
    return False


def _crosses_antimeridian(polygon: Polygon) -> bool:
    if _ring_crosses(polygon.exterior.coords):
        return True
    return any(_ring_crosses(r.coords) for r in polygon.interiors)


def _shift_ring(coords):
    """Map longitudes from [-180, 180] to [0, 360) so the ring is continuous."""
    out = []
    for c in coords:
        lon = c[0]
        if lon < 0:
            lon += 360.0
        out.append((lon,) + tuple(c[1:]))
    return out


def _unshift(polygon: Polygon) -> Polygon:
    """Map longitudes from [180, 360] back to [-180, 0]."""

    def fix(coords):
        return [(c[0] - 360.0,) + tuple(c[1:]) for c in coords]

    return Polygon(fix(polygon.exterior.coords), [fix(r.coords) for r in polygon.interiors])


def _polygons(geom: BaseGeometry) -> List[Polygon]:
    """Flatten any geometry into its non-empty polygonal parts."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        parts: List[Polygon] = []
        for g in geom.geoms:
            parts.extend(_polygons(g))
        return parts
    return []


def _valid(geom: BaseGeometry) -> BaseGeometry:
    return geom if geom.is_valid else make_valid(geom)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` into pieces that do not cross the antimeridian.

    ``polygon`` must have lon/lat coordinates (EPSG:4326) with longitudes in
    [-180, 180]. If it does not cross the antimeridian it is returned as the
    single element of a list, unchanged. Otherwise the returned polygons are
    valid, lie entirely within one hemisphere each (touching lon = ±180 only
    along their boundary), and together cover exactly the same surface region.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("split_antimeridian expects a shapely Polygon")
    if polygon.is_empty or not _crosses_antimeridian(polygon):
        return [polygon]

    # Rebuild the polygon in a continuous 0..360 longitude frame.
    shifted = Polygon(
        _shift_ring(polygon.exterior.coords),
        [_shift_ring(r.coords) for r in polygon.interiors],
    )
    shifted = _valid(shifted)

    west_box = box(0.0, -90.0, 180.0, 90.0)   # stays in [0, 180]
    east_box = box(180.0, -90.0, 360.0, 90.0)  # maps back to [-180, 0]

    result: List[Polygon] = []
    for part in _polygons(_valid(shifted.intersection(west_box))):
        result.append(part)
    for part in _polygons(_valid(shifted.intersection(east_box))):
        result.append(_valid(_unshift(part)))

    # Drop degenerate slivers and ensure every piece is a valid Polygon.
    final: List[Polygon] = []
    for p in result:
        for q in _polygons(_valid(p)):
            if q.area > 0:
                final.append(q)
    return final
```