"""Split polygons that cross the antimeridian into antimeridian-safe pieces."""

import math

from shapely.affinity import translate
from shapely.geometry import Polygon, box


def _crosses_antimeridian(coords):
    return any(
        abs(coords[i][0] - coords[i - 1][0]) > 180 for i in range(1, len(coords))
    )


def _unwrap_ring(coords):
    if not coords:
        return coords
    unwrapped = [tuple(coords[0])]
    offset = 0.0
    for i in range(1, len(coords)):
        x = coords[i][0]
        rest = tuple(coords[i][1:])
        prev_x = unwrapped[-1][0]
        candidate = x + offset
        while candidate - prev_x > 180:
            offset -= 360
            candidate = x + offset
        while candidate - prev_x < -180:
            offset += 360
            candidate = x + offset
        unwrapped.append((candidate,) + rest)
    return unwrapped


def _shift_ring(coords, k):
    if k == 0:
        return coords
    return [(coord[0] + k * 360,) + tuple(coord[1:]) for coord in coords]


def _align_interior_ring(coords, ext_min_x, ext_max_x):
    unwrapped = _unwrap_ring(coords)
    xs = [c[0] for c in unwrapped]
    mid_hole = (min(xs) + max(xs)) / 2.0
    mid_ext = (ext_min_x + ext_max_x) / 2.0
    k = round((mid_ext - mid_hole) / 360.0)
    return _shift_ring(unwrapped, k)


def split_antimeridian(polygon: Polygon) -> list:
    """Split a lon/lat polygon that crosses the antimeridian into valid pieces.

    Returns a list of polygons covering the same region as ``polygon``, none
    of which crosses (or touches other than at its edge) the antimeridian.
    A polygon that does not cross the antimeridian is returned unchanged as
    a single-element list.
    """
    exterior_coords = list(polygon.exterior.coords)
    interior_coords_list = [list(ring.coords) for ring in polygon.interiors]

    crosses = _crosses_antimeridian(exterior_coords) or any(
        _crosses_antimeridian(c) for c in interior_coords_list
    )
    if not crosses:
        return [polygon]

    unwrapped_exterior = _unwrap_ring(exterior_coords)
    ext_xs = [c[0] for c in unwrapped_exterior]
    ext_min_x, ext_max_x = min(ext_xs), max(ext_xs)

    unwrapped_interiors = [
        _align_interior_ring(c, ext_min_x, ext_max_x) for c in interior_coords_list
    ]

    unwrapped_polygon = Polygon(unwrapped_exterior, unwrapped_interiors)

    min_x, _, max_x, _ = unwrapped_polygon.bounds
    k_min = math.floor((min_x + 180) / 360)
    k_max = math.floor((max_x + 180) / 360)

    result = []
    for k in range(k_min, k_max + 1):
        clip = box(k * 360 - 180, -90.0, k * 360 + 180, 90.0)
        piece = unwrapped_polygon.intersection(clip)
        if piece.is_empty:
            continue
        piece = translate(piece, xoff=-k * 360)
        for geom in getattr(piece, "geoms", [piece]):
            if isinstance(geom, Polygon) and not geom.is_empty:
                result.append(geom)

    return result