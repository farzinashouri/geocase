"""Split shapely polygons that cross the antimeridian (EPSG:4326, lon in [-180, 180]).

Importing this module has no side effects.
"""

import math

from shapely.geometry import Polygon, box
from shapely.affinity import translate


def _crosses(coords):
    """True if any consecutive vertices jump more than 180 degrees in longitude."""
    coords = list(coords)
    for i in range(1, len(coords)):
        if abs(coords[i][0] - coords[i - 1][0]) > 180.0:
            return True
    return False


def _unwrap(coords):
    """Return coords with longitudes unwrapped into a continuous range.

    Consecutive antimeridian jumps (deltas beyond +/-180) are removed by
    accumulating the shortest-arc delta, so the ring becomes continuous even if
    that pushes longitudes outside [-180, 180].
    """
    coords = list(coords)
    xs = [coords[0][0]]
    for i in range(1, len(coords)):
        d = coords[i][0] - coords[i - 1][0]
        if d > 180.0:
            d -= 360.0
        elif d < -180.0:
            d += 360.0
        xs.append(xs[-1] + d)
    return [(xs[i], coords[i][1]) for i in range(len(coords))]


def _polys(geom):
    """Extract the polygonal components (positive area) of an arbitrary geometry."""
    if geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return [geom]
    if gt in ("MultiPolygon", "GeometryCollection"):
        out = []
        for g in geom.geoms:
            out.extend(_polys(g))
        return out
    return []


def split_antimeridian(polygon):
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        Longitude/latitude coordinates in EPSG:4326 with longitudes in
        [-180, 180]. Vertices that cross the antimeridian jump between values
        near +180 and near -180.

    Returns
    -------
    list of shapely.geometry.Polygon
        Valid polygons covering exactly the same region, none of which crosses
        the antimeridian (they may touch it only at their edge). A polygon that
        does not cross the antimeridian is returned unchanged as a single-element
        list.
    """
    rings = [polygon.exterior.coords] + [r.coords for r in polygon.interiors]
    if not any(_crosses(r) for r in rings):
        return [polygon]

    # Unwrap the exterior into a continuous longitude frame.
    ext = _unwrap(polygon.exterior.coords)
    exs = [p[0] for p in ext]
    ex_center = (min(exs) + max(exs)) / 2.0

    # Unwrap each hole, then shift it by a multiple of 360 so it sits inside the
    # exterior's frame.
    holes = []
    for interior in polygon.interiors:
        h = _unwrap(interior.coords)
        hxs = [p[0] for p in h]
        h_center = (min(hxs) + max(hxs)) / 2.0
        k = round((ex_center - h_center) / 360.0)
        holes.append([(x + 360.0 * k, y) for x, y in h])

    unwrapped = Polygon(ext, holes)
    if not unwrapped.is_valid:
        unwrapped = unwrapped.buffer(0)

    xmin, _ymin, xmax, _ymax = unwrapped.bounds

    # Bands are 360-wide strips centred on 360*b, i.e. x in [360*b - 180, 360*b + 180].
    # A small epsilon keeps geometry that merely touches x = 180 in the lower band.
    eps = 1e-9
    b_lo = math.floor((xmin + eps + 180.0) / 360.0)
    b_hi = math.floor((xmax - eps + 180.0) / 360.0)

    result = []
    for b in range(b_lo, b_hi + 1):
        clip = box(360.0 * b - 180.0, -1.0e6, 360.0 * b + 180.0, 1.0e6)
        piece = unwrapped.intersection(clip)
        if piece.is_empty:
            continue
        # Translate the band back into [-180, 180].
        piece = translate(piece, xoff=-360.0 * b)
        for g in _polys(piece):
            if g.area > 0.0:
                if not g.is_valid:
                    g = g.buffer(0)
                for gg in _polys(g):
                    if gg.area > 0.0:
                        result.append(gg)

    return result