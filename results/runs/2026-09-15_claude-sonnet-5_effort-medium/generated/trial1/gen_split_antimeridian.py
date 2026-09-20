"""Split a longitude/latitude polygon that crosses the antimeridian into
one or more polygons that each stay within [-180, 180] and do not cross
the antimeridian.
"""

import math

from shapely.affinity import translate
from shapely.geometry import Polygon, box


def _unwrap_ring(coords):
    """Adjust longitudes along a ring so consecutive points never jump by
    more than 180 degrees, by adding/subtracting multiples of 360."""
    coords = list(coords)
    if not coords:
        return coords
    out = [coords[0]]
    for x, y in coords[1:]:
        prev_x = out[-1][0]
        while x - prev_x > 180:
            x -= 360
        while x - prev_x < -180:
            x += 360
        out.append((x, y))
    return out


def _crosses_antimeridian(coords):
    coords = list(coords)
    for i in range(len(coords) - 1):
        if abs(coords[i + 1][0] - coords[i][0]) > 180:
            return True
    return False


def split_antimeridian(polygon):
    """Return a list of shapely Polygons covering the same region as
    `polygon`, none of which crosses the antimeridian.

    If `polygon` does not cross the antimeridian, it is returned unchanged
    as the sole element of the list.
    """
    exterior = list(polygon.exterior.coords)
    interiors = [list(ring.coords) for ring in polygon.interiors]

    crosses = _crosses_antimeridian(exterior) or any(
        _crosses_antimeridian(ring) for ring in interiors
    )
    if not crosses:
        return [polygon]

    unwrapped_exterior = _unwrap_ring(exterior)
    unwrapped_interiors = [_unwrap_ring(ring) for ring in interiors]
    unwrapped_polygon = Polygon(unwrapped_exterior, unwrapped_interiors)

    minx, _, maxx, _ = unwrapped_polygon.bounds
    k_lo = math.floor(minx / 360) - 1
    k_hi = math.ceil(maxx / 360) + 1

    results = []
    for k in range(k_lo, k_hi + 1):
        clip_box = box(k * 360 - 180, -90, k * 360 + 180, 90)
        piece = unwrapped_polygon.intersection(clip_box)
        if piece.is_empty:
            continue
        shifted = translate(piece, xoff=-k * 360)
        if shifted.geom_type == "Polygon":
            if shifted.area > 0:
                results.append(shifted)
        elif shifted.geom_type == "MultiPolygon":
            for geom in shifted.geoms:
                if geom.area > 0:
                    results.append(geom)

    return results