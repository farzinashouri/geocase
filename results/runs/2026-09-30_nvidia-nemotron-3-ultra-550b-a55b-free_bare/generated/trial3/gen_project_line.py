from shapely.geometry import LineString
import pyproj

def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 (lon/lat) to a projected CRS (dst_epsg)
    by densifying the geodesic segments to within 25 km tolerance.

    Parameters
    ----------
    line : shapely.LineString
        Input line in EPSG:4326 (coordinates are longitude, latitude).
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.LineString
        LineString in the target CRS (coordinates in projected units, typically meters)
        approximating the geodesic path between input vertices.
    """
    if not isinstance(line, LineString):
        raise TypeError("Input must be a shapely LineString")
    if line.is_empty:
        return LineString()

    # Geodetic object for WGS84 ellipsoid
    geod = pyproj.Geod(ellps="WGS84")
    # Transformer from geographic (EPSG:4326) to target CRS
    transformer = pyproj.Transformer.from_crs(4326, dst_epsg, always_xy=True)

    # Sampling interval in meters (5 km ensures deviation << 25 km)
    DEL_S = 5000.0

    coords = list(line.coords)
    geo_points = []  # list of (lon, lat) tuples

    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]

        # Skip zero-length segments
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        if dist < 1e-6:
            if i == 0:
                geo_points.append((lon1, lat1))
            continue

        # Get geodesic line as a shapely LineString with points every DEL_S meters
        segment = geod.line(lon1, lat1, lon2, lat2, del_s=DEL_S)
        seg_coords = list(segment.coords)

        if i == 0:
            geo_points.extend(seg_coords)
        else:
            # Skip the first point to avoid duplication
            geo_points.extend(seg_coords[1:])

    # Transform all geographic points to target CRS
    lons, lats = zip(*geo_points)
    xs, ys = transformer.transform(lons, lats)

    # Create LineString in target CRS
    projected_coords = list(zip(xs, ys))
    return LineString(projected_coords)