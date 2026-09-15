```python
"""Split a longitude/latitude Polygon that crosses the antimeridian into
one or more Polygons that each stay within [-180, 180]."""

import math

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon, box


def _has_jump(xs):
    return any(abs(xs[i + 1] - xs[i]) > 180 for i in range(len(xs) - 1))


def _unwrap(xs):
    return np.unwrap(np.asarray(xs, dtype=float), period=360.0)


def _extract_polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    if geom.geom_type == "GeometryCollection":
        result = []
        for g in geom.geoms:
            result.extend(_extract_polygons(g))
        return result
    return []


def split_antimeridian(polygon):
    ext_coords = list(polygon.exterior.coords)
    ext_xs_orig = [c[0] for c in ext_coords]
    ext_ys = [c[1] for c in ext_coords]

    interior_coords = [list(ring.coords) for ring in polygon.interiors]

    crosses = _has_jump(ext_xs_orig) or any(
        _has_jump([c[0] for c in ring]) for ring in interior_coords
    )
    if not crosses:
        return [polygon]

    ext_xs = _unwrap(ext_xs_orig)
    ext_mean = float(ext_xs.mean())
    ext_ring = list(zip(ext_xs.tolist(), ext_ys))

    interior_rings = []
    for ring in interior_coords:
        xs = [c[0] for c in ring]
        ys = [c[1] for c in ring]
        xs_u = _unwrap(xs)
        shift = round((ext_mean - float(xs_u.mean())) / 360.0) * 360.0
        xs_u = xs_u + shift
        interior_rings.append(list(zip(xs_u.tolist(), ys)))

    unwrapped_poly = Polygon(ext_ring, interior_rings)
    minx, miny, maxx, maxy = unwrapped_poly.bounds

    k_min = math.ceil((minx - 180.0) / 360.0)
    k_max = math.floor((maxx - 180.0) / 360.0)
    split_xs = sorted(
        180.0 + 360.0 * k
        for k in range(k_min, k_max + 1)
        if minx < 180.0 + 360.0 * k < maxx
    )

    boundaries = [minx - 1.0] + split_xs + [maxx + 1.0]

    results = []
    for i in range(len(boundaries) - 1):
        lo, hi = boundaries[i], boundaries[i + 1]
        clip_box = box(lo, miny - 1.0, hi, maxy + 1.0)
        piece = unwrapped_poly.intersection(clip_box)
        pieces = _extract_polygons(piece)
        if not pieces:
            continue

        mid_x = (lo + hi) / 2.0
        shift_back = -360.0 * math.floor((mid_x + 180.0) / 360.0)

        for p in pieces:
            if p.is_empty or p.area == 0:
                continue
            results.append(translate(p, xoff=shift_back))

    return results
```