import shapely.geometry
import pyproj
import numpy as np


def project_line(line, dst_epsg):
    coords = list(line.coords)
    
    if len(coords) < 2:
        return line
    
    geod = pyproj.Geod(ellps='WGS84')
    output_vertices = [coords[0]]
    
    max_segment_length = 20000
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        distance, az12, _ = geod.inv(lon1, lat1, lon2, lat2)
        
        num_segments = max(1, int(np.ceil(distance / max_segment_length)))
        
        segment_distances = np.linspace(0, distance, num_segments + 1)
        
        for seg_dist in segment_distances[1:]:
            lon, lat, _ = geod.fwd(lon1, lat1, az12, seg_dist)
            output_vertices.append((lon, lat))
    
    transformer = pyproj.Transformer.from_crs(
        'EPSG:4326',
        f'EPSG:{dst_epsg}',
        always_xy=True
    )
    
    lons, lats = zip(*output_vertices)
    xs, ys = transformer.transform(lons, lats)
    
    return shapely.geometry.LineString(zip(xs, ys))