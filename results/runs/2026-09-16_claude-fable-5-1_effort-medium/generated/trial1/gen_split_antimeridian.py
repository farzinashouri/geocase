"""Split polygons that cross the antimeridian into pieces that do not.

Coordinates are longitude/latitude in EPSG:4326 with longitudes in [-180, 180].
A polygon "crosses" the antimeridian when consecutive vertices jump by more than
180 degrees of longitude (e.g. from 179 to -179).
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Polygon,
    box,
)
from shapely.validation import make_valid

Coord = Tuple[float, ...]


def _crosses(coords: Sequence[Coord]) -> bool:
    """True if any consecutive pair of vertices jumps more than 180 deg in longitude."""
    for (x0, *_), (x1, *_) in zip(coords, coords[1:]):
        if abs(x1 - x0) > 180.0:
            return True
    return False


def _unwrap(coords: Sequence[Coord]) -> List[Coord]:
    """Make longitudes continuous by adding/subtracting 360 at each jump."""
    if not coords:
        return []
    out: List[Coord] = [tuple(coords[0])]
    offset = 0.0
    prev_x = coords[0][0]
    for c in coords[1:]:
        x = c[0]
        delta = x - prev_x
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        out.append((x + offset, *c[1:]))
        prev_x = x
    return out


def _shift(coords: Sequence[Coord], dx: float) -> List[Coord]:
    return [(c[0] + dx, *c[1:]) for c in coords]


def _polygons_of(geom) -> List[Polygon]:
    """Flatten any geometry into a list of non-empty Polygons."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        result: List[Polygon] = []
        for part in geom.geoms:
            result.extend(_polygons_of(part))
        return result
    return []


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Returns a list of valid polygons covering the same area as ``polygon``,
    none of which crosses the antimeridian. If ``polygon`` does not cross
    it, the polygon is returned unchanged as a single-element list.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("split_antimeridian expects a shapely Polygon")
    if polygon.is_empty:
        return [polygon]

    exterior = list(polygon.exterior.coords)
    holes = [list(r.coords) for r in polygon.interiors]

    if not _crosses(exterior) and not any(_crosses(h) for h in holes):
        return [polygon]

    # Unwrap the exterior ring so it is continuous in longitude.
    ext_unwrapped = _unwrap(exterior)
    shell = Polygon(ext_unwrapped)

    # Unwrap each hole and shift it by a multiple of 360 so it sits inside
    # the unwrapped exterior.
    hole_rings: List[List[Coord]] = []
    for hole in holes:
        hu = _unwrap(hole)
        chosen = hu
        probe = Polygon(hu).representative_point()
        for dx in (0.0, 360.0, -360.0, 720.0, -720.0):
            candidate = _shift(hu, dx)
            pt = Polygon(candidate).representative_point()
            if shell.contains(pt):
                chosen = candidate
                break
        else:
            # Fall back to the shift that brings the hole nearest the shell.
            cx = shell.centroid.x
            best_dx = min((0.0, 360.0, -360.0), key=lambda d: abs(probe.x + d - cx))
            chosen = _shift(hu, best_dx)
        hole_rings.append(chosen)

    unwrapped = Polygon(ext_unwrapped, hole_rings)
    if not unwrapped.is_valid:
        unwrapped = make_valid(unwrapped)

    minx, miny, maxx, maxy = unwrapped.bounds
    # Enumerate the 360-degree "worlds" the unwrapped geometry spans.
    import math

    k_min = int(math.floor((minx + 180.0) / 360.0))
    k_max = int(math.floor((maxx + 180.0) / 360.0))
    if maxx == -180.0 + 360.0 * k_max:  # touching the boundary exactly
        k_max -= 1
    k_max = max(k_max, k_min)

    pieces: List[Polygon] = []
    for k in range(k_min, k_max + 1):
        lo = -180.0 + 360.0 * k
        hi = lo + 360.0
        clip = box(lo, min(miny, -90.0) - 1.0, hi, max(maxy, 90.0) + 1.0)
        part = unwrapped.intersection(clip)
        for poly in _polygons_of(part):
            if k != 0:
                shell_c = _shift(list(poly.exterior.coords), -360.0 * k)
                holes_c = [_shift(list(r.coords), -360.0 * k) for r in poly.interiors]
                poly = Polygon(shell_c, holes_c)
            if not poly.is_valid:
                poly = make_valid(poly)
            for p in _polygons_of(poly):
                if p.area > 0.0:
                    pieces.append(p)

    return pieces