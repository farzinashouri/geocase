"""Split shapely polygons that cross the antimeridian (lon = ±180).

Coordinates are longitude/latitude in EPSG:4326 with longitudes in
[-180, 180].  A crossing is detected when consecutive vertices jump by
more than 180 degrees of longitude.  The polygon is first "unwrapped"
into a continuous longitude range (e.g. 170 .. 190), then clipped to
each 360-degree band bounded by lines lon = 180 + 360*k, and each piece
is shifted back into [-180, 180].
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

Coord = Tuple[float, ...]


def _unwrap_ring(coords: Sequence[Coord]) -> List[Coord]:
    """Make longitudes continuous by adding ±360 whenever a jump > 180 occurs.

    If the ring encircles a pole, the unwrapped ring will not close (its
    first and last longitudes differ by 360); in that case the ring is
    closed through the nearer pole.
    """
    if not coords:
        return []
    out: List[Coord] = [tuple(coords[0])]
    offset = 0.0
    prev_lon = coords[0][0]
    for c in coords[1:]:
        lon = c[0]
        d = lon - prev_lon
        if d > 180:
            offset -= 360
        elif d < -180:
            offset += 360
        out.append((lon + offset,) + tuple(c[1:]))
        prev_lon = lon

    first, last = out[0], out[-1]
    if abs(last[0] - first[0]) > 1e-9:
        # Polar ring: close it via the pole on the side of the mean latitude.
        mean_lat = sum(p[1] for p in out) / len(out)
        pole = 90.0 if mean_lat >= 0 else -90.0
        out = out + [(last[0], pole), (first[0], pole), first]
    return out


def _crosses(coords: Sequence[Coord]) -> bool:
    return any(
        abs(coords[i + 1][0] - coords[i][0]) > 180 for i in range(len(coords) - 1)
    )


def _shift(poly: Polygon, dlon: float) -> Polygon:
    def sh(ring):
        return [(c[0] + dlon,) + tuple(c[1:]) for c in ring]

    return Polygon(sh(poly.exterior.coords), [sh(r.coords) for r in poly.interiors])


def _polygons(geom: BaseGeometry) -> List[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [g for g in geom.geoms if not g.is_empty]
    if hasattr(geom, "geoms"):
        out: List[Polygon] = []
        for g in geom.geoms:
            out.extend(_polygons(g))
        return out
    return []


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` into pieces that do not cross the antimeridian.

    Returns ``[polygon]`` unchanged when no crossing is present.
    """
    if polygon.is_empty:
        return [polygon]

    rings = [list(polygon.exterior.coords)] + [
        list(r.coords) for r in polygon.interiors
    ]
    if not any(_crosses(r) for r in rings):
        return [polygon]

    exterior = _unwrap_ring(rings[0])
    ext_poly = Polygon(exterior)
    holes: List[List[Coord]] = []
    for r in rings[1:]:
        h = _unwrap_ring(r)
        # Align the hole's longitude band with the unwrapped exterior.
        hp = Polygon(h)
        rep = hp.representative_point()
        for k in (0, 1, -1, 2, -2):
            if ext_poly.contains(
                type(rep)(rep.x + 360 * k, rep.y)
            ):
                if k:
                    h = [(c[0] + 360 * k,) + tuple(c[1:]) for c in h]
                break
        holes.append(h)

    unwrapped = make_valid(Polygon(exterior, holes))
    minx, miny, maxx, maxy = unwrapped.bounds

    # Bands are [180 + 360*(k-1), 180 + 360*k]; band k maps back by -360*k.
    import math

    k_lo = math.floor((minx - 180) / 360) + 1
    k_hi = math.floor((maxx - 180) / 360) + 1
    if maxx == 180 + 360 * (k_hi - 1):
        k_hi -= 1

    result: List[Polygon] = []
    for k in range(k_lo, k_hi + 1):
        lo = 180 + 360 * (k - 1)
        hi = 180 + 360 * k
        band = box(lo, min(miny, -90) - 1, hi, max(maxy, 90) + 1)
        piece = unwrapped.intersection(band)
        for p in _polygons(piece):
            p = _shift(p, -360 * k) if k else p
            if not p.is_valid:
                p = make_valid(p)
            for q in _polygons(p):
                if q.area > 0:
                    result.append(q)
    return result