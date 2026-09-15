"""Project a WGS84 LineString into a projected CRS while preserving geodesic shape."""

from pyproj import Geod, Transformer
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")
_MAX_ERROR_M = 25_000.0
_MAX_DEPTH = 24


def _midpoint_error(lon1, lat1, lon2, lat2, to_proj, to_geo):
    az12, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if dist == 0.0:
        return 0.0, None

    true_lon, true_lat, _ = _GEOD.fwd(lon1, lat1, az12, dist / 2.0)

    x1, y1 = to_proj.transform(lon1, lat1)
    x2, y2 = to_proj.transform(lon2, lat2)
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    approx_lon, approx_lat = to_geo.transform(mx, my)

    _, _, err = _GEOD.inv(true_lon, true_lat, approx_lon, approx_lat)
    return err, (true_lon, true_lat)


def _densify(lon1, lat1, lon2, lat2, to_proj, to_geo, depth=0):
    if depth >= _MAX_DEPTH:
        return []

    err, mid = _midpoint_error(lon1, lat1, lon2, lat2, to_proj, to_geo)
    if mid is None or err <= _MAX_ERROR_M:
        return []

    mid_lon, mid_lat = mid
    left = _densify(lon1, lat1, mid_lon, mid_lat, to_proj, to_geo, depth + 1)
    right = _densify(mid_lon, mid_lat, lon2, lat2, to_proj, to_geo, depth + 1)
    return left + [(mid_lon, mid_lat)] + right


def project_line(line, dst_epsg):
    to_proj = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    to_geo = Transformer.from_crs(dst_epsg, 4326, always_xy=True)

    coords = [(c[0], c[1]) for c in line.coords]

    densified = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        densified.extend(_densify(lon1, lat1, lon2, lat2, to_proj, to_geo))
        densified.append((lon2, lat2))

    projected = [to_proj.transform(lon, lat) for lon, lat in densified]
    return LineString(projected)