"""Project a WGS84 LineString into a projected CRS along geodesic paths.

The input line's vertices are longitude/latitude pairs (EPSG:4326).  A straight
segment between two such vertices is *not* the shortest path on the ellipsoid,
and even the true geodesic is generally a curve once drawn in a projected CRS.
So the line is densified on the ellipsoid before projection: every input segment
is replaced by a chain of intermediate geodesic points spaced closely enough
that the polyline drawn through them stays within the required tolerance of the
geodesic everywhere.
"""

from __future__ import annotations

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line"]

#: Required accuracy of the output polyline with respect to the true geodesic.
TOLERANCE_M = 25_000.0

#: Spacing between densified points, in metres.  The sagitta (maximum offset)
#: of a chord subtending an arc of length ``s`` on a sphere of radius ``R`` is
#: ``R * (1 - cos(s / 2R))``; at s = 50 km that is under 50 m, three orders of
#: magnitude inside TOLERANCE_M.  The generous margin also absorbs the extra
#: deviation introduced by projection distortion over a single step, which is
#: what actually governs accuracy for an ill-suited destination CRS.
STEP_M = 50_000.0


def _densify(geod: Geod, lon1: float, lat1: float, lon2: float, lat2: float):
    """Yield intermediate points of the geodesic from 1 to 2, endpoints excluded."""
    distance = geod.inv(lon1, lat1, lon2, lat2)[2]
    n_extra = int(distance // STEP_M)
    if n_extra <= 0:
        return
    yield from geod.npts(lon1, lat1, lon2, lat2, n_extra)


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Reproject a WGS84 line into ``dst_epsg``, following geodesic courses.

    Parameters
    ----------
    line:
        A ``LineString`` whose coordinates are (longitude, latitude) degrees in
        EPSG:4326.
    dst_epsg:
        EPSG code of the projected CRS to return the line in.

    Returns
    -------
    LineString
        The line in ``dst_epsg``, densified so that it traces the geodesic
        between each pair of consecutive input vertices to within 25 km.
    """
    if line.is_empty:
        raise ValueError("cannot project an empty LineString")

    src_crs = CRS.from_epsg(4326)
    dst_crs = CRS.from_epsg(dst_epsg)
    geod = src_crs.get_geod()
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    coords = [(x, y) for x, y, *_ in line.coords]

    densified = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        densified.extend(_densify(geod, lon1, lat1, lon2, lat2))
        densified.append((lon2, lat2))

    lons = [pt[0] for pt in densified]
    lats = [pt[1] for pt in densified]
    xs, ys = transformer.transform(lons, lats)

    projected = [
        (x, y)
        for x, y in zip(xs, ys)
        if x == x and y == y and abs(x) != float("inf") and abs(y) != float("inf")
    ]
    if len(projected) < 2:
        raise ValueError(f"line does not project into EPSG:{dst_epsg}")

    return LineString(projected)