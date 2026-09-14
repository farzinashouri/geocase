from shapely.geometry import LineString
import pyproj
import math

def project_line(line, dst_epsg):
    EARTH_RADIUS_KM = 6371.0
    MAX_STEP_KM = math.sqrt(8 * EARTH_RADIUS_KM * 25)
    
    geod = pyproj.Geod(ellps='WGS84')
    transformer = pyproj.Transformer.from_crs(
        'EPSG:4326',
        f'EPSG:{dst_epsg}',
        always_xy=True
    )
    
    coords = list(line.coords)
    densified_coords = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        az12, az21, distance_m = geod.inv(lon1, lat1, lon2, lat2)
        distance_km = distance_m / 1000
        
        num_segments = max(1, math.ceil(distance_km / MAX_STEP_KM))
        
        densified_coords.append((lon1, lat1))
        
        if num_segments > 1:
            intermediate = geod.npts(lon1, lat1, lon2, lat2, num_segments - 1)
            densified_coords.extend(intermediate)
    
    densified_coords.append(coords[-1])
    
    lons, lats = zip(*densified_coords)
    xs, ys = transformer.transform(lons, lats)
    transformed_coords = list(zip(xs, ys))
    
    return LineString(transformed_coords)