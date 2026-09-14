from shapely.geometry import LineString
import pyproj
import math


def project_line(line, dst_epsg):
    """
    Project a LineString from WGS84 to a destination CRS, interpolating geodesic points.
    
    Args:
        line: shapely LineString with coordinates in EPSG:4326 (lon, lat)
        dst_epsg: integer EPSG code of destination CRS
    
    Returns:
        shapely LineString in destination CRS, with geodesic paths interpolated to within 25 km
    """
    coords = list(line.coords)
    geod = pyproj.Geod(ellps='WGS84')
    
    interpolated_coords = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        # Calculate geodesic distance and azimuth
        az12, _, distance_m = geod.inv(lon1, lat1, lon2, lat2)
        distance_km = distance_m / 1000
        
        # Add starting point of this segment
        interpolated_coords.append((lon1, lat1))
        
        # Determine number of segments needed for 25 km max spacing
        num_segments = max(1, math.ceil(distance_km / 25))
        
        # Add intermediate points along the geodesic
        if num_segments > 1:
            for j in range(1, num_segments):
                dist_along = (j / num_segments) * distance_m
                lon, lat, _ = geod.fwd(lon1, lat1, az12, dist_along)
                interpolated_coords.append((lon, lat))
    
    # Add final point
    interpolated_coords.append(coords[-1])
    
    # Create CRS objects and transformer
    wgs84 = pyproj.CRS.from_epsg(4326)
    dst_crs = pyproj.CRS.from_epsg(dst_epsg)
    transformer = pyproj.Transformer.from_crs(wgs84, dst_crs, always_xy=True)
    
    # Transform all points to destination CRS
    transformed_coords = []
    for lon, lat in interpolated_coords:
        x, y = transformer.transform(lon, lat)
        transformed_coords.append((x, y))
    
    # Return as LineString
    return LineString(transformed_coords)