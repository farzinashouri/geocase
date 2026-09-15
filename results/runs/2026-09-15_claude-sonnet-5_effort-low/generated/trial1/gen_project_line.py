"""Project a WGS84 LineString to a projected CRS, densified along geodesics."""

from shapely.geometry import LineString
from pyproj import Geod, Transformer

_MAX_SEGMENT_M = 25_000.0
_GEOD = Geod(ellps="WGS84")


def project_line(line, dst_epsg):
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    densified = [coords[0][:2]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
        n_segments = max(1, int(dist // _MAX_SEGMENT_M) + 1)
        if n_segments > 1:
            pts = _GEOD.npts(lon1, lat1, lon2, lat2, n_segments - 1)
            densified.extend(pts)
        densified.append((lon2, lat2))

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
    projected = [transformer.transform(lon, lat) for lon, lat in densified]

    return LineString(projected)