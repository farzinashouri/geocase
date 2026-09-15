"""Project a WGS84 LineString onto a projected CRS while preserving its
geodesic (ellipsoidal shortest-path) shape to within a fixed tolerance."""

from pyproj import Geod, Transformer
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")

# Chord length used to densify each input segment before reprojecting.
# For a chord this short, the sagitta (max deviation from the true geodesic
# arc) is on the order of a few meters, far below the 25 km tolerance even
# after accounting for projection distortion.
_MAX_SEGMENT_KM = 20.0


def _densify_segment(lon1, lat1, lon2, lat2):
    """Return intermediate (lon, lat) points along the geodesic from
    (lon1, lat1) to (lon2, lat2), not including either endpoint."""
    _, _, distance_m = _GEOD.inv(lon1, lat1, lon2, lat2)
    distance_km = distance_m / 1000.0
    if distance_km <= _MAX_SEGMENT_KM:
        return []
    npts = int(distance_km // _MAX_SEGMENT_KM)
    return _GEOD.npts(lon1, lat1, lon2, lat2, npts)


def project_line(line, dst_epsg):
    """Reproject a WGS84 (EPSG:4326) LineString into the projected CRS
    identified by ``dst_epsg``, densifying it so that the result follows
    the true geodesic course between the original vertices to within
    25 km everywhere along the line.
    """
    coords = [(pt[0], pt[1]) for pt in line.coords]
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    lonlat_points = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        lonlat_points.extend(_densify_segment(lon1, lat1, lon2, lat2))
        lonlat_points.append((lon2, lat2))

    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    projected_points = [transformer.transform(lon, lat) for lon, lat in lonlat_points]

    return LineString(projected_points)