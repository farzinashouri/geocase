"""Split polygons that cross the antimeridian (the +/-180 degree meridian).

The single public entry point is :func:`split_antimeridian`.  Coordinates are
assumed to be longitude/latitude in EPSG:4326 with longitudes in [-180, 180].
A polygon that crosses the antimeridian has consecutive vertices that jump
between values near +180 and values near -180.  Such a polygon is "unwrapped"
into a continuous longitude range, clipped into 360-degree-wide strips, and
each strip is shifted back into [-180, 180].  The result is a list of valid
polygons that together cover exactly the same region of the Earth's surface;
none of them crosses the antimeridian, though pieces may share an edge along
lon = 180 or lon = -180.

Polygons that enclose a pole (rings that wind fully around the globe) are not
supported; they are not representable as a simple lon/lat polygon in the
first place.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

_Coord = Tuple[float, float]


def _ring_coords(ring) -> List[_Coord]:
    """Return the (x, y) vertices of a shapely LinearRing (closed)."""
    return [(float(x), float(y)) for x, y, *_ in ring.coords]


def _crosses(coords: Sequence[_Coord]) -> bool:
    """True if any consecutive pair of vertices jumps by more than 180 degrees."""
    for (x0, _), (x1, _) in zip(coords, coords[1:]):
        if abs(x1 - x0) > 180.0:
            return True
    return False


def _unwrap(coords: Sequence[_Coord]) -> List[_Coord]:
    """Make longitudes continuous by adding multiples of 360 after each jump."""
    if not coords:
        return []
    out: List[_Coord] = [coords[0]]
    offset = 0.0
    prev_x = coords[0][0]
    for x, y in coords[1:]:
        delta = x - prev_x
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        out.append((x + offset, y))
        prev_x = x
    return out


def _mean_lon(coords: Sequence[_Coord]) -> float:
    # Skip the closing vertex so it is not counted twice.
    pts = coords[:-1] if len(coords) > 1 and coords[0] == coords[-1] else coords
    return sum(x for x, _ in pts) / len(pts)


def _align_to_shell(hole: List[_Coord], shell_center: float) -> List[_Coord]:
    """Shift a hole by a multiple of 360 so it sits inside the unwrapped shell."""
    shift = 360.0 * round((shell_center - _mean_lon(hole)) / 360.0)
    if shift == 0.0:
        return hole
    return [(x + shift, y) for x, y in hole]


def _iter_polygons(geom: BaseGeometry) -> Iterable[Polygon]:
    """Yield every non-empty Polygon contained in ``geom`` (any nesting)."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _iter_polygons(part)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in EPSG:4326 with longitudes in [-180, 180].

    Returns
    -------
    list of Polygon
        If ``polygon`` does not cross the antimeridian, ``[polygon]`` (the very
        same object).  Otherwise, a list of valid polygons, each entirely within
        the longitude range [-180, 180], whose union covers the same surface
        region as the input.
    """
    if polygon.is_empty:
        return [polygon]

    shell = _ring_coords(polygon.exterior)
    holes = [_ring_coords(r) for r in polygon.interiors]

    if not _crosses(shell) and not any(_crosses(h) for h in holes):
        return [polygon]

    # 1. Unwrap every ring into a continuous longitude range, then place each
    #    hole in the same 360-degree "copy" of the world as the shell.
    shell_u = _unwrap(shell)
    shell_center = _mean_lon(shell_u)
    holes_u = [_align_to_shell(_unwrap(h), shell_center) for h in holes]

    unwrapped: BaseGeometry = Polygon(shell_u, holes_u)
    if not unwrapped.is_valid:
        unwrapped = shapely.make_valid(unwrapped)

    # 2. Clip into strips [-180 + 360k, 180 + 360k] and shift each back by 360k.
    minx, _, maxx, _ = unwrapped.bounds
    k_min = math.floor((minx + 180.0) / 360.0)
    k_max = math.floor((maxx + 180.0) / 360.0)

    pieces: List[Polygon] = []
    for k in range(k_min, k_max + 1):
        shift = 360.0 * k
        strip = box(-180.0 + shift, -90.0, 180.0 + shift, 90.0)
        clipped = shapely.intersection(unwrapped, strip)
        if clipped.is_empty:
            continue
        if shift != 0.0:
            clipped = shapely.transform(
                clipped, lambda c, s=shift: c - [s, 0.0]
            )
        for part in _iter_polygons(clipped):
            if not part.is_valid:
                part_valid = shapely.make_valid(part)
                pieces.extend(_iter_polygons(part_valid))
            else:
                pieces.append(part)

    # 3. Preserve any non-Polygon leftovers as nothing; polygons only.
    return pieces