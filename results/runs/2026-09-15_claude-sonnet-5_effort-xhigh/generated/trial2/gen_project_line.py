"""Project a WGS84 geodesic LineString into a projected CRS.

The public entry point is :func:`project_line`, which takes a
``shapely.geometry.LineString`` whose vertices are longitude/latitude
coordinates in EPSG:4326 and returns a new ``LineString`` expressed in a
target projected CRS. Consecutive input vertices are treated as
waypoints joined by geodesics (shortest paths on the WGS84 ellipsoid),
and the result is densified with extra vertices so that it tracks each
geodesic to within 25 km everywhere along its length.
"""

import math

from pyproj import Geod, Transformer
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")

# Maximum length (in meters) of any sub-segment used to approximate a
# geodesic with a straight line before projecting. For a great-circle-like
# arc of this length, the chord-to-arc deviation (sagitta) is roughly
# L^2 / (8 * R) ~= 200 m for L = 100 km and Earth radius R ~= 6371 km,
# which leaves a wide safety margin under the required 25 km tolerance
# even after accounting for typical projection distortion.
_MAX_SEGMENT_METERS = 100_000.0


def _densify_segment(lon1, lat1, lon2, lat2):
    """Return interior lon/lat points that subdivide the geodesic between
    (lon1, lat1) and (lon2, lat2) into pieces no longer than
    _MAX_SEGMENT_METERS. Endpoints are not included in the result."""
    _, _, distance_m = _GEOD.inv(lon1, lat1, lon2, lat2)
    if distance_m <= _MAX_SEGMENT_METERS:
        return []
    npts = int(math.ceil(distance_m / _MAX_SEGMENT_METERS)) - 1
    return _GEOD.npts(lon1, lat1, lon2, lat2, npts)


def project_line(line, dst_epsg):
    """Project a WGS84 (EPSG:4326) LineString onto a projected CRS.

    Args:
        line: A shapely LineString with longitude/latitude coordinates
            in EPSG:4326.
        dst_epsg: Integer EPSG code of the destination projected CRS.

    Returns:
        A shapely LineString in the CRS identified by dst_epsg whose
        vertices trace the geodesic path between each pair of
        consecutive input vertices to within 25 km everywhere.
    """
    coords = [(x, y) for x, y, *_ in line.coords]

    lonlat_points = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        lonlat_points.extend(_densify_segment(lon1, lat1, lon2, lat2))
        lonlat_points.append((lon2, lat2))

    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    projected_points = [transformer.transform(lon, lat) for lon, lat in lonlat_points]

    return LineString(projected_points)