import numpy as np
from pyproj import Geod, Transformer
from shapely.geometry import LineString


def project_line(line, dst_epsg):
    """
    Project a LineString from EPSG:4326 to a projected CRS, densifying along geodesics
    so that the returned line traces the ellipsoidal geodesic between each pair of
    consecutive input vertices to within 25 km everywhere.

    Parameters
    ----------
    line : shapely.LineString
        Input line in EPSG:4326 (longitude, latitude).
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.LineString
        Line in the target CRS approximating the geodesic paths.
    """
    geod = Geod(ellps="WGS84")
    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)

    # Extract 2D coordinates (ignore Z if present)
    coords = [(c[0], c[1]) for c in line.coords]
    if len(coords) < 2:
        return LineString()

    # Sample the geodesic at most every 10 km (well within the 25 km tolerance)
    MAX_SEGMENT_LENGTH = 10000.0  # meters

    geo_points = [coords[0]]

    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]

        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)

        if dist <= MAX_SEGMENT_LENGTH:
            geo_points.append((lon2, lat2))
        else:
            n_segments = int(np.ceil(dist / MAX_SEGMENT_LENGTH))
            npts = n_segments - 1
            intermediates = geod.npts(lon1, lat1, lon2, lat2, npts)
            geo_points.extend(intermediates)
            geo_points.append((lon2, lat2))

    lons, lats = zip(*geo_points)
    xs, ys = transformer.transform(lons, lats)
    return LineString(zip(xs, ys))