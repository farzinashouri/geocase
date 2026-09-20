Bash access needs approval, so I wrote and reviewed this without running it here.

```python
"""Split EPSG:4326 polygons that cross the antimeridian.

The single public entry point is :func:`split_antimeridian`.  Importing this
module has no side effects.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_HALF = 180.0

Coord = Tuple[float, float]
Ring = List[Coord]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` where it crosses the antimeridian.

    ``polygon`` is a shapely :class:`~shapely.geometry.Polygon` whose
    coordinates are longitude/latitude in EPSG:4326, with longitudes in
    ``[-180, 180]``.  A polygon crossing the antimeridian is expected to be
    encoded the usual way: consecutive vertices jump between values near
    ``+180`` and values near ``-180``.

    Returns a list of valid polygons that together cover exactly the same
    region of the Earth's surface, none of which crosses the antimeridian
    (they may touch it along an edge).  A polygon that does not cross the
    antimeridian is returned unchanged as a single-element list.

    Any ``z`` values are dropped from polygons that are actually split, since
    the split is computed by clipping in the longitude/latitude plane.

    Raises
    ------
    TypeError
        If ``polygon`` is not a :class:`~shapely.geometry.Polygon`.
    ValueError
        If a ring winds all the way around the globe.  Such a polygon encloses
        a pole, and recovering the intended region needs assumptions this
        function deliberately does not make.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    rings = [_ring_coords(polygon.exterior)]
    rings.extend(_ring_coords(interior) for interior in polygon.interiors)

    if not any(_crosses(ring) for ring in rings):
        return [polygon]

    unwrapped = _unwrap_polygon(rings)

    # Slide the unwrapped polygon so its western edge sits in [-180, 180),
    # then clip it against successive 360-degree-wide strips and fold each
    # piece back into [-180, 180].
    minx, miny, _, maxy = unwrapped.bounds
    shift = -_PERIOD * math.floor((minx + _HALF) / _PERIOD)
    if shift:
        unwrapped = translate(unwrapped, xoff=shift)
    maxx = unwrapped.bounds[2]

    pieces: List[Polygon] = []
    for index in range(max(1, math.ceil((maxx + _HALF) / _PERIOD))):
        lo = -_HALF + index * _PERIOD
        strip = box(lo, miny - 1.0, lo + _PERIOD, maxy + 1.0)
        for part in _polygon_parts(unwrapped.intersection(strip)):
            pieces.append(translate(part, xoff=-index * _PERIOD) if index else part)
    return pieces


def _ring_coords(ring) -> Ring:
    """Return a ring's coordinates as 2D float tuples."""
    return [(float(c[0]), float(c[1])) for c in ring.coords]


def _crosses(ring: Ring) -> bool:
    """True if consecutive vertices jump across the antimeridian."""
    return any(abs(b[0] - a[0]) > _HALF for a, b in zip(ring, ring[1:]))


def _unwrap_ring(ring: Ring) -> Ring:
    """Make a ring continuous in longitude by undoing the +-180 wraparound.

    Each jump larger than half a period is assumed to be a wraparound rather
    than real motion, so the shortest step between consecutive vertices is
    taken and the accumulated offset is carried forward.
    """
    unwrapped = [ring[0]]
    offset = 0.0
    for (prev_x, _), (x, y) in zip(ring, ring[1:]):
        delta = x - prev_x
        if delta > _HALF:
            offset -= _PERIOD
        elif delta < -_HALF:
            offset += _PERIOD
        unwrapped.append((x + offset, y))
    if offset:
        raise ValueError(
            "ring winds around the globe (net longitude change of "
            f"{offset:+.0f} degrees); such a polygon encloses a pole and "
            "cannot be split at the antimeridian alone"
        )
    return unwrapped


def _unwrap_polygon(rings: Sequence[Ring]) -> BaseGeometry:
    """Unwrap shell and holes into a common, continuous longitude frame."""
    shell = _unwrap_ring(rings[0])
    shell_mid = _mid_x(shell)

    holes = []
    for ring in rings[1:]:
        hole = _unwrap_ring(ring)
        # Each ring is unwrapped relative to its own first vertex, so a hole
        # can land a whole period away from the shell that contains it.  The
        # shell spans less than 360 degrees, so the period that brings the two
        # midpoints closest is the one that puts the hole back inside.
        periods = round((shell_mid - _mid_x(hole)) / _PERIOD)
        if periods:
            hole = [(x + periods * _PERIOD, y) for x, y in hole]
        holes.append(hole)

    unwrapped: BaseGeometry = Polygon(shell, holes)
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)
    return unwrapped


def _mid_x(ring: Ring) -> float:
    xs = [x for x, _ in ring]
    return (min(xs) + max(xs)) / 2.0


def _polygon_parts(geometry: BaseGeometry) -> List[Polygon]:
    """Collect the non-empty polygonal parts of a geometry.

    Clipping can also yield lines or points where the polygon merely touches a
    strip boundary; those carry no area and are discarded.
    """
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    parts: List[Polygon] = []
    for part in getattr(geometry, "geoms", ()):
        parts.extend(_polygon_parts(part))
    return parts
```