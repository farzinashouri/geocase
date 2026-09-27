"""Project a WGS84 lon/lat LineString onto a projected CRS, following the geodesic.

Each input segment is densified along the true ellipsoidal geodesic so that the
straight-line chords of the output polyline never stray more than 25 km from the
actual shortest-path course, then every vertex is transformed into ``dst_epsg``.
"""

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Spacing between densified geodesic points, in metres. With points no more than
# this far apart along the geodesic, the maximum deviation of the connecting
# chords from the geodesic stays well under the required 25 km tolerance.
_MAX_SPACING_M = 10_000.0

_GEOD = Geod(ellps="WGS84")


def project_line(line, dst_epsg):
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("LineString must have at least two vertices")

    # Build the densified geodesic path in lon/lat.
    lonlat = [coords[0][:2]]
    for (lon0, lat0), (lon1, lat1) in zip(coords[:-1], coords[1:]):
        _, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
        n_intermediate = int(dist // _MAX_SPACING_M)
        if n_intermediate > 0:
            for lon, lat in _GEOD.npts(lon0, lat0, lon1, lat1, n_intermediate):
                lonlat.append((lon, lat))
        lonlat.append((lon1, lat1))

    transformer = Transformer.from_crs(4326, int(dst_epsg), always_xy=True)
    lons, lats = zip(*lonlat)
    xs, ys = transformer.transform(lons, lats)

    return LineString(list(zip(xs, ys)))