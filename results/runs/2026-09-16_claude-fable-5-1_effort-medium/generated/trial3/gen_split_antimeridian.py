"""Split EPSG:4326 polygons that cross the antimeridian (the +/-180 meridian).

The single public function is :func:`split_antimeridian`.  It has no import-time
side effects and depends only on the standard library and shapely 2.x.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_XY = Tuple[float, float]


def _crosses(coords: Sequence[_XY]) -> bool:
    """True when any consecutive pair of vertices jumps more than 180 degrees."""
    return any(abs(b[0] - a[0]) > 180.0 for a, b in zip(coords, coords[1:]))


def _unwrap(coords: Sequence[_XY]) -> Tuple[List[_XY], float]:
    """Make a ring's longitudes continuous by adding +/-360 across each jump.

    Returns the unwrapped coordinates and the net offset at the end of the ring.
    A non-zero net offset means the ring winds around a pole, which cannot be
    represented as a simple longitude/latitude polygon.
    """
    out: List[_XY] = []
    offset = 0.0
    prev_x = None
    for x, y in coords:
        if prev_x is not None:
            d = x - prev_x
            if d > 180.0:
                offset -= 360.0
            elif d < -180.0:
                offset += 360.0
        out.append((x + offset, y))
        prev_x = x
    return out, offset


def _xy(ring) -> List[_XY]:
    return [(float(c[0]), float(c[1])) for c in ring.coords]


def _polygons(geom) -> Iterable[Polygon]:
    """Yield the non-degenerate Polygon parts of any geometry."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        if geom.area > 0.0:
            yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)):
        for part in geom.geoms:
            yield from _polygons(part)


def _valid_polygons(geom) -> List[Polygon]:
    if not geom.is_valid:
        geom = make_valid(geom)
    return list(_polygons(geom))


def _shift_and_clamp(poly: Polygon, dx: float) -> Polygon:
    """Translate longitudes by ``dx`` and clamp them into [-180, 180]."""

    def _f(a):
        a = a.copy()
        a[:, 0] = a[:, 0] + dx
        a[:, 0] = a[:, 0].clip(-180.0, 180.0)
        return a

    return shapely.transform(poly, _f)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split a lon/lat polygon at the antimeridian.

    Parameters
    ----------
    polygon
        A shapely ``Polygon`` in EPSG:4326 with longitudes in [-180, 180].  A
        polygon crossing the antimeridian has consecutive vertices that jump
        between values near +180 and values near -180.

    Returns
    -------
    list of Polygon
        Valid polygons covering exactly the same region of the sphere, none of
        which crosses the antimeridian (they may touch it along an edge).  A
        polygon that does not cross the antimeridian is returned unchanged as a
        one-element list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If a ring winds around a pole (net longitude change of +/-360), which
        cannot be represented without adding pole vertices.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    exterior = _xy(polygon.exterior)
    interiors = [_xy(r) for r in polygon.interiors]

    if not _crosses(exterior) and not any(_crosses(r) for r in interiors):
        return [polygon]

    # 1. Unwrap every ring into a continuous longitude frame.
    ext_unwrapped, net = _unwrap(exterior)
    if net != 0.0:
        raise ValueError("polygon winds around a pole; cannot split at the antimeridian")

    ext_poly = Polygon(ext_unwrapped)
    ext_minx, _, ext_maxx, _ = ext_poly.bounds

    holes: List[List[_XY]] = []
    for ring in interiors:
        ring_unwrapped, net = _unwrap(ring)
        if net != 0.0:
            raise ValueError("interior ring winds around a pole; cannot split at the antimeridian")
        # Each ring unwraps relative to its own first vertex, so a hole may sit
        # a whole number of turns away from the exterior.  Pick the turn that
        # places it inside the exterior.
        hole_poly = Polygon(ring_unwrapped)
        hole_minx, _, hole_maxx, _ = hole_poly.bounds
        k_lo = math.floor((ext_minx - hole_maxx) / 360.0) - 1
        k_hi = math.ceil((ext_maxx - hole_minx) / 360.0) + 1
        chosen = ring_unwrapped
        for k in range(k_lo, k_hi + 1):
            dx = 360.0 * k
            candidate = [(x + dx, y) for x, y in ring_unwrapped]
            if ext_poly.contains(Polygon(candidate).representative_point()):
                chosen = candidate
                break
        holes.append(chosen)

    unwrapped = Polygon(ext_unwrapped, holes)

    # 2. Cut the unwrapped polygon at every antimeridian image strictly inside
    #    its longitude range: x = 180 + 360 k.
    minx, miny, maxx, maxy = unwrapped.bounds
    k_first = math.ceil((minx - 180.0) / 360.0)
    k_last = math.floor((maxx - 180.0) / 360.0)
    cuts = [180.0 + 360.0 * k for k in range(k_first, k_last + 1) if minx < 180.0 + 360.0 * k < maxx]
    if not cuts:
        # The jumps were degenerate (e.g. a vertex at exactly -180 followed by
        # one at +180) and the region lies on one side only.
        return [polygon]

    edges = [minx - 1.0] + cuts + [maxx + 1.0]
    pad_y0, pad_y1 = min(miny, -90.0) - 1.0, max(maxy, 90.0) + 1.0

    pieces: List[Polygon] = []
    for a, b in zip(edges, edges[1:]):
        clipped = unwrapped.intersection(box(a, pad_y0, b, pad_y1))
        # Map this strip back onto [-180, 180].
        centre = 0.5 * (a + b)
        dx = -360.0 * round(centre / 360.0)
        for part in _valid_polygons(clipped):
            pieces.extend(_valid_polygons(_shift_and_clamp(part, dx)))

    return pieces