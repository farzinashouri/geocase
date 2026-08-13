"""Oracle for project_line (VEC-0029): densify *before* reprojection. The
oracle projects true geodesic waypoints (Geod.npts) and requires the returned
line to pass close to them; densifying after (or never) puts the midpoint of a
long line hundreds of kilometres off."""

import pyproj
from shapely.geometry import LineString, Point

from geocase.benchmark._oracle_utils import GEOD

DST = 3857
_T = pyproj.Transformer.from_crs(4326, DST, always_xy=True)


def _max_offset_m(got: LineString, lonlat_pts) -> float:
    """Planar distance in EPSG:3857 from the line to projected waypoints,
    de-inflated by the Mercator scale factor at each waypoint's latitude."""
    import math

    worst = 0.0
    for lon, lat in lonlat_pts:
        p = Point(_T.transform(lon, lat))
        worst = max(worst, got.distance(p) * math.cos(math.radians(lat)))
    return worst


def build_checks(f):
    def control():
        line = LineString([(13.0, 52.0), (13.05, 52.02)])
        got = f(line, DST)
        pts = GEOD.npts(13.0, 52.0, 13.05, 52.02, 5)
        off = _max_offset_m(got, pts)
        endpoints_ok = (
            Point(_T.transform(13.0, 52.0)).distance(Point(got.coords[0])) < 50
            and Point(_T.transform(13.05, 52.02)).distance(Point(got.coords[-1])) < 50
        )
        ok = endpoints_ok and off < 1000
        return ok, f"endpoints_ok={endpoints_ok}, max offset {off:.0f} m"

    def long_line():
        line = LineString([(-60.0, 0.0), (60.0, 60.0)])
        got = f(line, DST)
        pts = GEOD.npts(-60.0, 0.0, 60.0, 60.0, 9)
        off = _max_offset_m(got, pts)
        ok = off < 25_000  # spec allows 1 km; vertex-only projection is >500 km off
        return ok, f"max offset from geodesic waypoints {off / 1000:.0f} km (limit 25)"

    return [
        ("short_line", "control", control),
        ("long_line_follows_geodesic", "edge", long_line),
    ]
