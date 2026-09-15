"""Project a WGS84 geodesic LineString into a projected CRS.

Densifies each input segment with intermediate geodesic points before
reprojection so the resulting polyline stays within 25 km of the true
geodesic course everywhere.
"""

from shapely.geometry import LineString
from pyproj import Geod, Transformer

# Sagitta of a 50 km great-circle chord is well under 1 km, leaving large
# margin against the 25 km tolerance even after projection distortion.
_MAX_SEGMENT_KM = 50.0


def project_line(line, dst_epsg):
    geod = Geod(ellps="WGS84")
    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)

    coords = [(pt[0], pt[1]) for pt in line.coords]

    lonlat_points = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        _, _, dist_m = geod.inv(lon1, lat1, lon2, lat2)
        dist_km = dist_m / 1000.0
        n_intermediate = max(0, int(dist_km // _MAX_SEGMENT_KM))
        if n_intermediate > 0:
            lonlat_points.extend(geod.npts(lon1, lat1, lon2, lat2, n_intermediate))
        lonlat_points.append((lon2, lat2))

    projected = [transformer.transform(lon, lat) for lon, lat in lonlat_points]
    return LineString(projected)