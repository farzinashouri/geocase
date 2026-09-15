"""Project a WGS84 LineString to a projected CRS, densifying it so the
resulting polyline follows the true geodesic between vertices to within
25 km everywhere along its length."""

import math

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# A geodesic chord this short deviates from the true geodesic arc by at most
# a few hundred meters (sagitta ~ d^2 / 8R), far below the 25 km tolerance,
# even after accounting for typical map-projection distortion.
_MAX_SEGMENT_METERS = 50_000.0

_GEOD = Geod(ellps="WGS84")


def project_line(line, dst_epsg):
    coords = list(line.coords)

    lonlat_points = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        _, _, distance_m = _GEOD.inv(lon1, lat1, lon2, lat2)
        n_segments = max(1, math.ceil(distance_m / _MAX_SEGMENT_METERS))
        if n_segments > 1:
            lonlat_points.extend(_GEOD.npts(lon1, lat1, lon2, lat2, n_segments - 1))
        lonlat_points.append((lon2, lat2))

    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    projected_points = [transformer.transform(lon, lat) for lon, lat in lonlat_points]

    return LineString(projected_points)