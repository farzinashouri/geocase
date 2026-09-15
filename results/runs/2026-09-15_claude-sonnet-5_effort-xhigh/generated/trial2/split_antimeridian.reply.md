```python
"""Split a longitude/latitude polygon that crosses the antimeridian into
one or more polygons that each stay within [-180, 180] and do not cross
the antimeridian.
"""

import math

from shapely.affinity import translate
from shapely.geometry import Polygon, box


def _ring_crosses(coords):
    """True if consecutive vertices in a ring jump by more than 180 degrees
    of longitude, indicating the raw coordinates wrap around the antimeridian."""
    for i in range(1, len(coords)):
        if abs(coords[i][0] - coords[i - 1][0]) > 180.0:
            return True
    return False


def _unroll_ring(coords):
    """Rewrite a ring's longitudes on a continuous (non-wrapping) number line,
    anchored at the ring's own first vertex, by adding +-360 whenever a big
    jump between consecutive raw vertices is detected."""
    unrolled = [coords[0]]
    offset = 0.0
    for i in range(1, len(coords)):
        prev_raw_x = coords[i - 1][0]
        raw_x, y = coords[i]
        dx = raw_x - prev_raw_x
        if dx > 180.0:
            offset -= 360.0
        elif dx < -180.0:
            offset += 360.0
        unrolled.append((raw_x + offset, y))
    return unrolled


def _best_alignment_offset(ring_coords, reference_polygon):
    """Pick the +-360 multiple to add to `ring_coords` so it best overlaps
    `reference_polygon`, used to nest interior rings (holes) onto the same
    unrolled sheet as the already-unrolled exterior ring."""
    best_k = 0
    best_score = -1.0
    for k in (-2, -1, 0, 1, 2):
        shifted = [(x + 360.0 * k, y) for x, y in ring_coords]
        candidate = Polygon(shifted)
        if not candidate.is_valid:
            candidate = candidate.buffer(0)
        score = reference_polygon.intersection(candidate).area
        if score > best_score:
            best_score = score
            best_k = k
    return best_k


def _iter_polygons(geom):
    """Flatten a Polygon/MultiPolygon/GeometryCollection into its
    non-degenerate Polygon parts."""
    if geom.is_empty:
        return
    geom_type = geom.geom_type
    if geom_type == "Polygon":
        if geom.area > 0:
            yield geom
    elif geom_type in ("MultiPolygon", "GeometryCollection"):
        for part in geom.geoms:
            yield from _iter_polygons(part)


def split_antimeridian(polygon):
    """Split a lon/lat Polygon (EPSG:4326, longitudes in [-180, 180]) that
    crosses the antimeridian into a list of polygons that together cover the
    same region and none of which crosses the antimeridian.

    If `polygon` does not cross the antimeridian, returns `[polygon]`.
    """
    exterior_coords = list(polygon.exterior.coords)
    interior_coords_list = [list(ring.coords) for ring in polygon.interiors]

    crosses = _ring_crosses(exterior_coords) or any(
        _ring_crosses(coords) for coords in interior_coords_list
    )
    if not crosses:
        return [polygon]

    unrolled_exterior = _unroll_ring(exterior_coords)
    exterior_only = Polygon(unrolled_exterior)
    if not exterior_only.is_valid:
        exterior_only = exterior_only.buffer(0)

    unrolled_interiors = []
    for coords in interior_coords_list:
        local = _unroll_ring(coords)
        k = _best_alignment_offset(local, exterior_only)
        aligned = [(x + 360.0 * k, y) for x, y in local]
        unrolled_interiors.append(aligned)

    unrolled_polygon = Polygon(unrolled_exterior, unrolled_interiors)
    if not unrolled_polygon.is_valid:
        unrolled_polygon = unrolled_polygon.buffer(0)

    minx, _, maxx, _ = unrolled_polygon.bounds
    k_min = int(math.floor((minx + 180.0) / 360.0)) - 1
    k_max = int(math.ceil((maxx - 180.0) / 360.0)) + 1

    pieces = []
    for k in range(k_min, k_max + 1):
        clip_box = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        clipped = unrolled_polygon.intersection(clip_box)
        for piece in _iter_polygons(clipped):
            pieces.append(translate(piece, xoff=-360.0 * k))

    return pieces
```