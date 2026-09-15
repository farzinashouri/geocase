```python
"""Antimeridian-safe polygon splitting.

A polygon in EPSG:4326 whose vertices are given as longitude/latitude pairs in
``[-180, 180]`` cannot represent a region spanning the antimeridian without
introducing a jump between longitudes near ``+180`` and near ``-180``.  Such a
polygon is geometrically wrong in the plane: the jumping edge sweeps all the way
back across the whole globe instead of taking the short way across 180°.

:func:`split_antimeridian` repairs that by unwrapping the ring longitudes into a
continuous frame (so the polygon becomes planar-correct, possibly extending past
±180), clipping the result against the 360°-wide longitude strips, and mapping
each clipped piece back into ``[-180, 180]``.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon, box

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_HALF = 180.0
_LAT_MIN = -90.0
_LAT_MAX = 90.0

Coord = Tuple[float, float]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` in EPSG:4326 with
        longitudes in ``[-180, 180]``.  It may cross the antimeridian, in which
        case consecutive vertices of one of its rings jump between values near
        ``+180`` and values near ``-180``.

    Returns
    -------
    list of Polygon
        Valid polygons whose union covers exactly the same region of the
        Earth's surface as the input, none of which crosses the antimeridian
        (pieces may *touch* it along their boundary).  A polygon that does not
        cross the antimeridian is returned unchanged as a single-element list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a :class:`~shapely.geometry.Polygon`.
    ValueError
        If a ring encircles a pole.  Such a ring has no closed representation in
        unwrapped longitude space and cannot be handled by longitude splitting
        alone.

    Notes
    -----
    Only the x/y coordinates are considered; any z values are dropped, as they
    are by any other clipping operation.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    rings = [_ring_coords(polygon.exterior)]
    rings.extend(_ring_coords(interior) for interior in polygon.interiors)

    if not any(_ring_crosses(ring) for ring in rings):
        return [polygon]

    shell = _unwrap_ring(rings[0])
    shell_center = _center_x(shell)
    holes = []
    for ring in rings[1:]:
        hole = _unwrap_ring(ring)
        # Each ring is unwrapped relative to its own first vertex, so a hole may
        # land a whole period away from the shell it belongs to.  Pull it back
        # onto the branch nearest the shell.
        shift = _PERIOD * round((shell_center - _center_x(hole)) / _PERIOD)
        if shift:
            hole = [(x + shift, y) for x, y in hole]
        holes.append(hole)

    unwrapped = _as_valid_polygonal(Polygon(shell, holes))
    if unwrapped.is_empty:
        return []

    minx, _, maxx, _ = unwrapped.bounds
    k_min = math.floor((minx + _HALF) / _PERIOD)
    k_max = math.floor((maxx + _HALF) / _PERIOD)

    pieces: List[Polygon] = []
    for k in range(k_min, k_max + 1):
        strip = box(_PERIOD * k - _HALF, _LAT_MIN, _PERIOD * k + _HALF, _LAT_MAX)
        clipped = unwrapped.intersection(strip)
        if clipped.is_empty:
            continue
        # Shift back into [-180, 180]; the clamp only absorbs the sub-ulp
        # overshoot that the shift can introduce at the clip boundary.
        shifted = _shift_lon(clipped, -_PERIOD * k)
        pieces.extend(_polygons(_as_valid_polygonal(shifted)))

    return [piece for piece in pieces if not piece.is_empty and piece.area > 0.0]


def _ring_coords(ring) -> List[Coord]:
    """Return a ring's vertices as 2D tuples, without the repeated closing one."""
    coords = [(float(c[0]), float(c[1])) for c in ring.coords]
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords.pop()
    return coords


def _ring_crosses(coords: Sequence[Coord]) -> bool:
    """True if any edge of the ring (including the closing one) jumps a period."""
    n = len(coords)
    return any(
        abs(coords[(i + 1) % n][0] - coords[i][0]) > _HALF for i in range(n)
    )


def _unwrap_ring(coords: Sequence[Coord]) -> List[Coord]:
    """Make ring longitudes continuous by removing ±360 jumps between vertices.

    The first vertex keeps its input longitude; every later vertex is offset by
    the multiple of 360 that makes each edge shorter than half a period, which
    is the only interpretation consistent with an edge that does not wrap the
    globe.
    """
    if not coords:
        return []

    unwrapped: List[Coord] = []
    offset = 0.0
    prev_x = coords[0][0]
    for x, y in coords:
        offset += _jump(x - prev_x)
        unwrapped.append((x + offset, y))
        prev_x = x

    # The closing edge must bring the accumulated offset back to zero, otherwise
    # the ring winds around the globe, i.e. it encloses a pole.
    if offset + _jump(coords[0][0] - prev_x) != 0.0:
        raise ValueError(
            "ring encircles a pole; it cannot be represented in unwrapped "
            "longitude space and cannot be split at the antimeridian"
        )
    return unwrapped


def _jump(delta: float) -> float:
    """The ±360 correction that turns an edge's longitude delta into the short way."""
    if delta > _HALF:
        return -_PERIOD
    if delta < -_HALF:
        return _PERIOD
    return 0.0


def _center_x(coords: Sequence[Coord]) -> float:
    xs = [x for x, _ in coords]
    return 0.5 * (min(xs) + max(xs))


def _shift_lon(geom, dx: float):
    """Translate longitudes by ``dx`` and clamp the result to ``[-180, 180]``."""

    def _transform(coords: np.ndarray) -> np.ndarray:
        out = np.array(coords, dtype=float, copy=True)
        out[:, 0] = np.clip(out[:, 0] + dx, -_HALF, _HALF)
        return out

    return shapely.transform(geom, _transform)


def _as_valid_polygonal(geom):
    """Return ``geom`` made valid, keeping only its polygonal parts."""
    if not geom.is_valid:
        geom = shapely.make_valid(geom)
    parts = _polygons(geom)
    if len(parts) == 1:
        return parts[0]
    return shapely.union_all(parts) if parts else shapely.Polygon()


def _polygons(geom) -> List[Polygon]:
    """Flatten any geometry into its non-empty polygonal components."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if hasattr(geom, "geoms"):
        return [p for part in geom.geoms for p in _polygons(part)]
    return []
```