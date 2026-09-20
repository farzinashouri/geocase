"""Project a WGS84 LineString onto a projected CRS along the geodesic path."""

from shapely.geometry import LineString
from pyproj import Geod, Transformer

_GEOD = Geod(ellps="WGS84")

# Arc length (in meters) below which a straight chord between two points sags
# only a few tens of meters off the true geodesic -- comfortably under the
# 25 km tolerance even after accounting for projection distortion.
_MAX_SEGMENT_M = 50_000.0
_MAX_SPLIT_DEPTH = 30


def _densify(lon1, lat1, lon2, lat2, depth=0):
    """Return points (excluding the start) tracing the geodesic from
    (lon1, lat1) to (lon2, lat2), splitting until each chord is short enough."""
    _, _, dist_m = _GEOD.inv(lon1, lat1, lon2, lat2)
    if dist_m <= _MAX_SEGMENT_M or depth >= _MAX_SPLIT_DEPTH:
        return [(lon2, lat2)]

    mid_lon, mid_lat = _GEOD.npts(lon1, lat1, lon2, lat2, 1)[0]
    return _densify(lon1, lat1, mid_lon, mid_lat, depth + 1) + _densify(
        mid_lon, mid_lat, lon2, lat2, depth + 1
    )


def project_line(line, dst_epsg):
    """Project a shapely LineString of EPSG:4326 lon/lat coordinates into the
    projected CRS `dst_epsg`, densifying it so the result follows the true
    geodesic between each pair of consecutive input vertices to within 25 km.
    """
    coords = [(x, y) for x, y, *_ in line.coords]

    lonlats = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        if (lon1, lat1) == (lon2, lat2):
            continue
        lonlats.extend(_densify(lon1, lat1, lon2, lat2))

    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    lons, lats = zip(*lonlats)
    xs, ys = transformer.transform(lons, lats)

    return LineString(zip(xs, ys))