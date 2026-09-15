```python
"""Split a polygon that crosses the antimeridian (180th meridian) into pieces.

Longitudes are assumed to be in EPSG:4326, expressed in the range [-180, 180].
A polygon crosses the antimeridian when consecutive ring vertices jump between
values near +180 and values near -180.
"""

import math

from shapely.affinity import translate
from shapely.geometry import Polygon, box


def _coords_2d(seq):
    return [(pt[0], pt[1]) for pt in seq]


def _ring_crosses(coords):
    return any(
        abs(coords[i][0] - coords[i - 1][0]) > 180.0
        for i in range(1, len(coords))
    )


def _unroll_ring(coords):
    """Shift vertices by multiples of 360 so the ring becomes continuous."""
    unrolled = [coords[0]]
    offset = 0.0
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i - 1][0]
        if dx > 180.0:
            offset -= 360.0
        elif dx < -180.0:
            offset += 360.0
        unrolled.append((coords[i][0] + offset, coords[i][1]))
    return unrolled


def _align_hole(hole_unrolled, exterior_unrolled):
    """Pick the 360-multiple shift that best nests the hole in the exterior."""
    ext_poly = Polygon(exterior_unrolled)
    if not ext_poly.is_valid:
        ext_poly = ext_poly.buffer(0)

    best_shift = 0.0
    best_overlap = -1.0
    for shift in (0.0, 360.0, -360.0):
        candidate = [(x + shift, y) for x, y in hole_unrolled]
        cand_poly = Polygon(candidate)
        if not cand_poly.is_valid:
            cand_poly = cand_poly.buffer(0)
        overlap = ext_poly.intersection(cand_poly).area
        if overlap > best_overlap:
            best_overlap = overlap
            best_shift = shift
    return [(x + best_shift, y) for x, y in hole_unrolled]


def _explode_polygons(geom, sink):
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        if geom.area > 0:
            sink.append(geom)
    elif geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        for part in geom.geoms:
            _explode_polygons(part, sink)


def split_antimeridian(polygon):
    """Split a polygon crossing the antimeridian into non-crossing polygons.

    Returns a list of valid shapely Polygons that together cover exactly the
    same region as the input. If the input does not cross the antimeridian,
    it is returned unchanged as a single-element list.
    """
    exterior = _coords_2d(polygon.exterior.coords)
    interiors = [_coords_2d(ring.coords) for ring in polygon.interiors]

    crosses = _ring_crosses(exterior) or any(_ring_crosses(ring) for ring in interiors)
    if not crosses:
        return [polygon]

    ext_unrolled = _unroll_ring(exterior)
    holes_unrolled = [
        _align_hole(_unroll_ring(ring), ext_unrolled) for ring in interiors
    ]

    big_polygon = Polygon(ext_unrolled, holes_unrolled)
    if not big_polygon.is_valid:
        big_polygon = big_polygon.buffer(0)

    minx, _, maxx, _ = big_polygon.bounds
    k_lo = int(math.floor((minx - 180.0) / 360.0))
    k_hi = int(math.ceil((maxx + 180.0) / 360.0))

    pieces = []
    for k in range(k_lo, k_hi + 1):
        window = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        clipped = big_polygon.intersection(window)
        if clipped.is_empty:
            continue
        clipped = translate(clipped, xoff=-360.0 * k)
        _explode_polygons(clipped, pieces)

    return pieces
```