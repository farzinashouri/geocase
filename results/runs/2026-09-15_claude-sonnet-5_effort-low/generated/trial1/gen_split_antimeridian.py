"""Split polygons that cross the antimeridian into non-crossing pieces."""

import math

from shapely.affinity import translate
from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Polygon,
    box,
)


def _unwrap_ring(coords):
    """Remove +/-360 jumps in a ring's longitudes, returning unwrapped coords
    and whether a jump (i.e. an antimeridian crossing) was found."""
    coords = list(coords)
    offset = 0.0
    crossed = False
    unwrapped = [coords[0]]
    for i in range(1, len(coords)):
        prev_lon = coords[i - 1][0]
        lon, lat = coords[i]
        dx = lon - prev_lon
        if dx > 180:
            offset -= 360
            crossed = True
        elif dx < -180:
            offset += 360
            crossed = True
        unwrapped.append((lon + offset, lat))
    return unwrapped, crossed


def _unwrap_polygon(polygon):
    exterior, crossed = _unwrap_ring(list(polygon.exterior.coords))
    interiors = []
    for ring in polygon.interiors:
        unwrapped_ring, ring_crossed = _unwrap_ring(list(ring.coords))
        interiors.append(unwrapped_ring)
        crossed = crossed or ring_crossed
    return Polygon(exterior, interiors), crossed


def _flatten_polygons(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        result = []
        for part in geom.geoms:
            result.extend(_flatten_polygons(part))
        return result
    return []


def split_antimeridian(polygon):
    """Split a lon/lat Polygon crossing the antimeridian into pieces that
    each stay within a single [-180, 180] wrap of longitude.

    If `polygon` does not cross the antimeridian, it is returned unchanged
    as a single-element list.
    """
    unwrapped, crossed = _unwrap_polygon(polygon)
    if not crossed:
        return [polygon]

    minx, miny, maxx, maxy = unwrapped.bounds
    k_min = math.floor((minx + 180) / 360)
    k_max = math.floor((maxx - 180) / 360)

    pad = max(abs(miny), abs(maxy), 1.0)
    results = []
    for k in range(k_min, k_max + 1):
        strip = box(-180 + 360 * k, miny - pad, 180 + 360 * k, maxy + pad)
        piece = unwrapped.intersection(strip)
        if piece.is_empty:
            continue
        shifted = translate(piece, xoff=-360 * k)
        results.extend(_flatten_polygons(shifted))

    return results