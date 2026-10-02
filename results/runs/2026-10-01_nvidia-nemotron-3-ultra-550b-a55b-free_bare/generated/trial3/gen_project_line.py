import pyproj
from shapely.geometry import LineString

def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 to a projected CRS by sampling the geodesic
    between consecutive vertices.

    The returned LineString approximates the geodesic (shortest path on the WGS84 ellipsoid)
    between each pair of input vertices, with a maximum deviation well within 25 km
    in the target CRS.

    Parameters
    ----------
    line : LineString
        Input line in EPSG:4326 (longitude, latitude).
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    LineString
        LineString in the target CRS.
    """
    if line.is_empty:
        return LineString()
    
    coords = list(line.coords)
    if len(coords) < 2:
        transformer = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
        xs, ys = transformer.transform([c[0] for c in coords], [c[1] for c in coords])
        return LineString(zip(xs, ys))
    
    geod = pyproj.Geod(ellps="WGS84")
    # Sampling interval along the geodesic (meters). 10 km ensures deviation << 25 km
    # after projection for any reasonable projected CRS.
    interval = 10000.0
    
    lons = []
    lats = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        # Geodesic distance on the ellipsoid
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        
        # Number of equally spaced intermediate points
        npts = max(0, int(dist / interval))
        
        if i == 0:
            lons.append(lon1)
            lats.append(lat1)
        
        if npts > 0:
            for lon, lat in geod.npts(lon1, lat1, lon2, lat2, npts):
                lons.append(lon)
                lats.append(lat)
        
        if i == len(coords) - 2:
            lons.append(lon2)
            lats.append(lat2)
    
    transformer = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
    xs, ys = transformer.transform(lons, lats)
    
    return LineString(zip(xs, ys))