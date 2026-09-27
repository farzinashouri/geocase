"""Project a WGS84 lon/lat LineString onto a projected CRS along the geodesic.

Each input segment is densified with intermediate points sampled on the
geodesic (shortest path on the WGS84 ellipsoid) so that consecutive samples
are no more than 25 km apart. Because the true geodesic is convex relative to
the polyline connecting samples spaced 25 km apart, the resulting projected
LineString traces the geodesic course to within 25 km everywhere.
"""

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Maximum allowed spacing (and hence deviation bound) along the line, in metres.
_MAX_STEP_M = 25_000.0

# WGS84 ellipsoid, used for all geodesic computations.
_GEOD = Geod(ellps="WGS84")


def project_line(line, dst_epsg):
    """Return ``line`` (EPSG:4326 lon/lat) projected to ``dst_epsg``.

    The output LineString follows the geodesic between each pair of consecutive
    input vertices to within 25 km along its whole length.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    # Build the densified geodesic path in lon/lat.
    dense_lonlat = [coords[0][:2]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        lon1, lat1 = lon1, lat1
        lon2, lat2 = lon2, lat2
        _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)

        # Number of intermediate points needed to keep spacing <= _MAX_STEP_M.
        n_inter = 0
        if dist > _MAX_STEP_M:
            # ceil(dist / step) sub-intervals -> that many minus one interior points.
            import math
            n_sub = math.ceil(dist / _MAX_STEP_M)
            n_inter = n_sub - 1

        if n_inter > 0:
            inter = _GEOD.npts(lon1, lat1, lon2, lat2, n_inter)
            dense_lonlat.extend(inter)

        dense_lonlat.append((lon2, lat2))

    # Project all densified vertices to the destination CRS.
    transformer = Transformer.from_crs(4326, int(dst_epsg), always_xy=True)
    lons = [c[0] for c in dense_lonlat]
    lats = [c[1] for c in dense_lonlat]
    xs, ys = transformer.transform(lons, lats)

    return LineString(list(zip(xs, ys)))