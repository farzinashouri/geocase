"""Project a WGS84 LineString into a projected CRS while preserving geodesic shape.

Densifies each input segment along the true geodesic (ellipsoidal shortest path)
so that after reprojection the resulting polyline stays within 25 km of the
actual geodesic course everywhere, then transforms the densified vertices into
the target CRS.
"""

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Spacing between densified points along each geodesic segment. Using a
# fraction of the 25 km tolerance leaves headroom for any additional
# deviation introduced by the projection itself over that distance.
_MAX_SEGMENT_LENGTH_M = 10_000.0

_GEOD = Geod(ellps="WGS84")


def project_line(line: LineString, dst_epsg: int) -> LineString:
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    densified_lonlat = [coords[0][:2]]

    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        _, _, segment_length_m = _GEOD.inv(lon1, lat1, lon2, lat2)

        if segment_length_m <= _MAX_SEGMENT_LENGTH_M:
            densified_lonlat.append((lon2, lat2))
            continue

        npts = int(segment_length_m // _MAX_SEGMENT_LENGTH_M)
        intermediates = _GEOD.npts(lon1, lat1, lon2, lat2, npts)
        densified_lonlat.extend(intermediates)
        densified_lonlat.append((lon2, lat2))

    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    projected = [transformer.transform(lon, lat) for lon, lat in densified_lonlat]

    return LineString(projected)