```python
"""Split polygons that cross the antimeridian (180th meridian) in EPSG:4326.

The module exposes a single public function, :func:`split_antimeridian`.
Importing it has no side effects.
"""

from __future__ import annotations

from typing import List, Sequence

from shapely.geometry import Polygon, box
from shapely.geometry.polygon import LinearRing
from shapely.ops import unary_union

__all__ = ["split_antimeridian"]

_LAT_MIN = -90.0
_LAT_MAX = 90.0


def _ring_coords(ring: LinearRing) -> List[Sequence[float]]:
    return [(float(x), float(y)) for x, y in ring.coords]


def _crosses(coords: Sequence[Sequence[float]]) -> bool:
    """True if consecutive vertices jump more than 180 degrees of longitude."""
    for (x0, _), (x1, _) in zip(coords, coords[1:]):
        if abs(x1 - x0) > 180.0:
            return True
    return False


def _unwrap(coords: Sequence[Sequence[float]]) -> List[Sequence[float]]:
    """Remove 360-degree discontinuities so longitudes vary continuously."""
    out = [(coords[0][0], coords[0][1])]
    offset = 0.0
    for (x0, _), (x1, y1) in zip(coords, coords[1:]):
        delta = x1 - x0
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        out.append((x1 + offset, y1))
    return out


def _align(coords: Sequence[Sequence[float]], reference: float) -> List[Sequence[float]]:
    """Shift a ring by a whole number of turns so it sits next to ``reference``."""
    mean = sum(x for x, _ in coords) / len(coords)
    shift = -360.0 * round((mean - reference) / 360.0)
    if shift == 0.0:
        return list(coords)
    return [(x + shift, y) for x, y in coords]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    ``polygon`` must be a shapely :class:`~shapely.geometry.Polygon` in
    EPSG:4326 with longitudes in [-180, 180].  A polygon that crosses the
    antimeridian has consecutive vertices jumping between values near +180
    and values near -180.

    Returns a list of valid polygons whose union covers exactly the same
    region of the Earth's surface as the input, none of which crosses the
    antimeridian (they may only touch it along their boundary at
    longitude +/-180).  A polygon that does not cross the antimeridian is
    returned unchanged as a single-element list.
    """
    if polygon.is_empty:
        return []

    shell = _ring_coords(polygon.exterior)
    holes = [_ring_coords(ring) for ring in polygon.interiors]

    if not _crosses(shell) and not any(_crosses(h) for h in holes):
        return [polygon]

    shell = _unwrap(shell)
    reference = sum(x for x, _ in shell) / len(shell)
    holes = [_align(_unwrap(h), reference) for h in holes]

    unwrapped = Polygon(shell, holes)
    if not unwrapped.is_valid:
        unwrapped = unwrapped.buffer(0)
    if unwrapped.is_empty:
        return []

    min_lon, _, max_lon, _ = unwrapped.bounds

    # Cut along every meridian that is a multiple of 180 degrees, then fold
    # each resulting band back into the [-180, 180] longitude window.
    first = int((min_lon // 180.0))
    last = int(-((-max_lon) // 180.0))  # ceil(max_lon / 180)
    pieces: List[Polygon] = []
    for k in range(first, max(last, first + 1)):
        band = box(180.0 * k, _LAT_MIN, 180.0 * (k + 1), _LAT_MAX)
        part = unwrapped.intersection(band)
        if part.is_empty:
            continue
        shift = -360.0 * round((180.0 * k + 90.0) / 360.0)
        if shift:
            part = _translate_lon(part, shift)
        pieces.extend(_polygons(part))

    if not pieces:
        return []

    merged = unary_union(pieces)
    return _polygons(merged)


def _translate_lon(geom, shift: float):
    from shapely.affinity import translate

    return translate(geom, xoff=shift)


def _polygons(geom) -> List[Polygon]:
    """Flatten a geometry to its (non-degenerate, valid) polygonal parts."""
    out: List[Polygon] = []
    parts = getattr(geom, "geoms", None)
    candidates = list(parts) if parts is not None else [geom]
    for part in candidates:
        if part.is_empty:
            continue
        if isinstance(part, Polygon):
            if not part.is_valid:
                part = part.buffer(0)
                out.extend(_polygons(part))
                continue
            if part.area > 0.0:
                out.append(part)
        elif getattr(part, "geoms", None) is not None:
            out.extend(_polygons(part))
    return out
```