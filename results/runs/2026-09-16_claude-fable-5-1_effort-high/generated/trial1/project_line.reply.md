Here is the module: it densifies each segment along the WGS84 geodesic, then adaptively bisects until the projected chord stays well within 25 km of the geodesic.

```python
"""Project a WGS84 LineString into a projected CRS while tracing the geodesic.

The straight segments of an EPSG:4326 line are not geodesics, and a straight
segment in a projected CRS is not one either.  ``project_line`` walks each
input segment along the ellipsoidal geodesic, adds vertices adaptively, and
returns a line whose projected chords stay within 25 km of the true geodesic.
"""

from __future__ import annotations

import math
from functools import lru_cache

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

TOLERANCE_M = 25_000.0

# The chord/geodesic separation is sampled at a few interior points only, so
# refinement stops at a fraction of the required tolerance to leave margin.
_TARGET_M = TOLERANCE_M / 5.0
# No output segment is longer than this along the geodesic, whatever the check says.
_MAX_SEGMENT_M = 100_000.0
# Below this length a segment is never split, which bounds the work near
# projection singularities (poles, antimeridian wrap) where no chord can fit.
_MIN_SEGMENT_M = 1.0
_MAX_DEPTH = 40
# Interior fractions at which the chord is compared to the geodesic.  These
# must match evenly spaced Geod.npts output with len(_CHECK_FRACTIONS) points.
_CHECK_FRACTIONS = (0.25, 0.5, 0.75)


@lru_cache(maxsize=32)
def _tools(dst_epsg: int):
    src = CRS.from_epsg(4326)
    dst = CRS.from_epsg(dst_epsg)
    fwd = Transformer.from_crs(src, dst, always_xy=True)
    inv = Transformer.from_crs(dst, src, always_xy=True)
    return Geod(ellps="WGS84"), fwd, inv


def _max_deviation(geod, fwd, inv, p, q):
    """Largest ellipsoidal distance (m) between sampled points on the geodesic
    p->q and the corresponding points on the straight projected chord.

    Returns NaN when the chord cannot be evaluated (non-finite projection).
    """
    px, py = fwd.transform(p[0], p[1])
    qx, qy = fwd.transform(q[0], q[1])
    if not all(math.isfinite(v) for v in (px, py, qx, qy)):
        return math.nan

    geo_pts = geod.npts(p[0], p[1], q[0], q[1], len(_CHECK_FRACTIONS))
    worst = 0.0
    for t, (glon, glat) in zip(_CHECK_FRACTIONS, geo_pts):
        cx = px + t * (qx - px)
        cy = py + t * (qy - py)
        clon, clat = inv.transform(cx, cy)
        if not (math.isfinite(clon) and math.isfinite(clat)):
            return math.nan
        _, _, d = geod.inv(glon, glat, clon, clat)
        if not math.isfinite(d):
            return math.nan
        worst = max(worst, d)
    return worst


def _densify_segment(geod, fwd, inv, p, q):
    """Return the vertices that follow p up to and including q."""
    _, _, dist = geod.inv(p[0], p[1], q[0], q[1])
    if not math.isfinite(dist) or dist <= 0.0:
        return [q]

    n = max(1, math.ceil(dist / _MAX_SEGMENT_M))
    interior = geod.npts(p[0], p[1], q[0], q[1], n - 1) if n > 1 else []
    nodes = [p] + [(float(x), float(y)) for x, y in interior] + [q]
    base_len = dist / n

    out = []
    for a, b in zip(nodes, nodes[1:]):
        # Depth-first, left-to-right, so output order follows the line.
        stack = [(a, b, 0)]
        while stack:
            s, e, depth = stack.pop()
            seg_len = base_len / (2 ** depth)
            split = False
            if depth < _MAX_DEPTH and seg_len > _MIN_SEGMENT_M:
                dev = _max_deviation(geod, fwd, inv, s, e)
                split = math.isfinite(dev) and dev > _TARGET_M
            if split:
                mlon, mlat = geod.npts(s[0], s[1], e[0], e[1], 1)[0]
                m = (float(mlon), float(mlat))
                stack.append((m, e, depth + 1))
                stack.append((s, m, depth + 1))
            else:
                out.append(e)
    return out


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a lon/lat (EPSG:4326) LineString into the CRS ``dst_epsg``.

    Consecutive input vertices are joined along the ellipsoidal geodesic, and
    enough vertices are inserted that every straight segment of the returned
    line lies within 25 km of that geodesic.
    """
    geod, fwd, inv = _tools(int(dst_epsg))

    verts = [(float(c[0]), float(c[1])) for c in line.coords]
    if len(verts) < 2:
        raise ValueError("LineString must have at least two vertices")

    out = [verts[0]]
    for p, q in zip(verts, verts[1:]):
        out.extend(_densify_segment(geod, fwd, inv, p, q))

    xs, ys = fwd.transform([v[0] for v in out], [v[1] for v in out])
    return LineString(list(zip(xs, ys)))
```