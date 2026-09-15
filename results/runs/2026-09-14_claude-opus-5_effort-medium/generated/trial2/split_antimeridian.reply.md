```python
"""Split shapely polygons that cross the antimeridian (180th meridian).

A polygon given in EPSG:4326 with longitudes in [-180, 180] that spans the
antimeridian has edges that jump from near +180 to near -180 (or back).  Such a
polygon is geometrically wrong: the jumping edge runs the long way around the
globe.  :func:`split_antimeridian` repairs it by unwrapping the longitudes into
a continuous frame, cutting the result along every meridian 180 + 360k, and
mapping each piece back into [-180, 180].

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence

from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

# Longitude width of one copy of the world.
_PERIOD = 360.0
# Tolerance used when snapping clipped coordinates back onto the cut meridian
# and when discarding slivers produced by the clip.
_SNAP_EPS = 1e-9
_AREA_EPS = 1e-12


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` whose coordinates are
        longitude/latitude in EPSG:4326, longitudes in [-180, 180].  The
        polygon may cross the antimeridian, in which case consecutive vertices
        jump between values near +180 and values near -180.

    Returns
    -------
    list of Polygon
        Polygons that together cover exactly the same region of the Earth's
        surface as the input, none of which crosses the antimeridian (they may
        touch it along an edge).  If the input does not cross the antimeridian
        it is returned unchanged as a single-element list.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")

    if polygon.is_empty:
        return [polygon]

    rings = [list(polygon.exterior.coords)] + [
        list(interior.coords) for interior in polygon.interiors
    ]
    if not any(_ring_wraps(ring) for ring in rings):
        return [polygon]

    unwrapped = _unwrap_polygon(polygon)
    if unwrapped is None or unwrapped.is_empty:
        return [polygon]

    min_lon, _, max_lon, _ = unwrapped.bounds

    # Strip k spans [360k - 180, 360k + 180]; find every strip the polygon meets.
    k_first = math.floor((min_lon + 180.0) / _PERIOD)
    k_last = math.floor((max_lon + 180.0) / _PERIOD)
    # A polygon ending exactly on a strip boundary should not open a new strip.
    if k_last > k_first and max_lon <= _PERIOD * k_last - 180.0 + _SNAP_EPS:
        k_last -= 1

    _, min_lat, _, max_lat = unwrapped.bounds
    pad = 1.0
    pieces: List[Polygon] = []
    for k in range(k_first, k_last + 1):
        strip = box(
            _PERIOD * k - 180.0,
            min_lat - pad,
            _PERIOD * k + 180.0,
            max_lat + pad,
        )
        clipped = unwrapped.intersection(strip)
        if clipped.is_empty:
            continue
        shifted = translate(clipped, xoff=-_PERIOD * k)
        for part in _as_polygons(shifted):
            snapped = _snap_to_world(part)
            if snapped is not None and snapped.area > _AREA_EPS:
                pieces.append(snapped)

    if not pieces:
        return [polygon]
    return pieces


def _ring_wraps(coords: Sequence[Sequence[float]]) -> bool:
    """True if consecutive vertices of ``coords`` jump across the antimeridian."""
    for (x0, *_), (x1, *_) in zip(coords, coords[1:]):
        if abs(x1 - x0) > 180.0:
            return True
    return False


def _unwrap_ring(coords: Sequence[Sequence[float]]) -> List[tuple]:
    """Remove the +/-360 jumps from a ring, producing continuous longitudes."""
    out: List[tuple] = []
    offset = 0.0
    prev_x = None
    for point in coords:
        x, y = float(point[0]), float(point[1])
        if prev_x is not None:
            offset += _PERIOD * round((prev_x - x) / _PERIOD)
        prev_x = x
        out.append((x + offset, y))
    # Keep the ring closed even if rounding nudged the closing vertex.
    if out and out[0] != out[-1]:
        out[-1] = (out[0][0], out[0][1])
    return out


def _unwrap_polygon(polygon: Polygon) -> Polygon | None:
    """Rebuild ``polygon`` with continuous longitudes, holes aligned to the shell."""
    shell = _unwrap_ring(polygon.exterior.coords)
    if len(shell) < 4:
        return None
    shell_xs = [x for x, _ in shell]
    shell_mid = 0.5 * (min(shell_xs) + max(shell_xs))

    holes: List[List[tuple]] = []
    for interior in polygon.interiors:
        ring = _unwrap_ring(interior.coords)
        if len(ring) < 4:
            continue
        ring_xs = [x for x, _ in ring]
        ring_mid = 0.5 * (min(ring_xs) + max(ring_xs))
        shift = _PERIOD * round((shell_mid - ring_mid) / _PERIOD)
        if shift:
            ring = [(x + shift, y) for x, y in ring]
        holes.append(ring)

    unwrapped = Polygon(shell, holes)
    if not unwrapped.is_valid:
        repaired = unwrapped.buffer(0)
        if repaired.is_empty:
            return None
        parts = _as_polygons(repaired)
        if not parts:
            return None
        unwrapped = parts[0] if len(parts) == 1 else MultiPolygon(parts)
    return unwrapped


def _as_polygons(geometry: BaseGeometry) -> List[Polygon]:
    """Flatten any geometry into its polygonal components."""
    if geometry.is_empty:
        return []
    geom_type = geometry.geom_type
    if geom_type == "Polygon":
        return [geometry]
    if geom_type in ("MultiPolygon", "GeometryCollection"):
        out: List[Polygon] = []
        for part in geometry.geoms:
            out.extend(_as_polygons(part))
        return out
    return []


def _snap_to_world(polygon: Polygon) -> Polygon | None:
    """Clamp longitudes into [-180, 180], snapping near-boundary coordinates."""

    def fix(coords: Iterable[Sequence[float]]) -> List[tuple]:
        fixed = []
        for point in coords:
            x, y = float(point[0]), float(point[1])
            if x > 180.0 - _SNAP_EPS:
                x = 180.0
            elif x < -180.0 + _SNAP_EPS:
                x = -180.0
            fixed.append((x, y))
        return fixed

    shell = fix(polygon.exterior.coords)
    holes = [fix(interior.coords) for interior in polygon.interiors]
    result = Polygon(shell, [h for h in holes if len(h) >= 4])
    if not result.is_valid:
        repaired = result.buffer(0)
        parts = _as_polygons(repaired)
        if not parts:
            return None
        result = max(parts, key=lambda p: p.area)
    return result if not result.is_empty else None
```