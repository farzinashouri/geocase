"""Oracle for to_rfc7946 (VEC-0008): EPSG:3857 input must be reprojected to
lon/lat, exterior rings must follow the right-hand rule, and there is no
``crs`` member. Expected lon/lat corners come from pyproj directly."""

import pyproj
from shapely.geometry import LinearRing, box

CORNERS = [(13.0, 52.0), (13.1, 52.0), (13.1, 52.1), (13.0, 52.1)]


def _ring_of(result):
    assert result["type"] == "Polygon", f"type is {result.get('type')!r}"
    return [tuple(c) for c in result["coordinates"][0]]


def _matches_corners(ring, tol=1e-6):
    hits = 0
    for cx, cy in CORNERS:
        if any(abs(x - cx) <= tol and abs(y - cy) <= tol for x, y in ring):
            hits += 1
    return hits == len(CORNERS)


def build_checks(f):
    def control():
        got = f(box(13.0, 52.0, 13.1, 52.1), 4326)
        ring = _ring_of(got)
        ccw = LinearRing(ring).is_ccw
        no_crs = "crs" not in got
        ok = _matches_corners(ring) and ccw and no_crs
        return ok, (
            f"corners_match={_matches_corners(ring)}, exterior_ccw={ccw}, "
            f"no_crs_member={no_crs}"
        )

    def mercator():
        t = pyproj.Transformer.from_crs(4326, 3857, always_xy=True)
        merc = [t.transform(x, y) for x, y in CORNERS]
        poly = box(
            min(x for x, _ in merc),
            min(y for _, y in merc),
            max(x for x, _ in merc),
            max(y for _, y in merc),
        )
        got = f(poly, 3857)
        ring = _ring_of(got)
        in_range = all(abs(x) <= 180 and abs(y) <= 90 for x, y in ring)
        # Web Mercator round trip is not exact in lat; 1e-6 deg is ~10 cm.
        ok = in_range and _matches_corners(ring, tol=1e-6) and LinearRing(ring).is_ccw
        return ok, (
            f"coords_in_lonlat_range={in_range}, corners_match_wgs84="
            f"{_matches_corners(ring, tol=1e-6)} (first coord {ring[0]})"
        )

    return [
        ("wgs84_polygon", "control", control),
        ("mercator_input_reprojected", "edge", mercator),
    ]
