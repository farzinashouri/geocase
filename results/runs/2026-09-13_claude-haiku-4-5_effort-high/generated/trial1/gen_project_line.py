from shapely.geometry import LineString
from pyproj import Geod, Transformer
import numpy as np


def project_line(line, dst_epsg):
    coords = list(line.coords)
    
    geod = Geod(ellps='WGS84')
    transformer = Transformer.from_crs('EPSG:4326', f'EPSG:{dst_epsg}', always_xy=True)
    
    densified_coords = [coords[0]]
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        az12, az21, distance = geod.inv(lon1, lat1, lon2, lat2)
        
        n_intermediate = max(0, int(np.ceil(distance / 25000)) - 1)
        
        if n_intermediate > 0:
            lons, lats = geod.npts(lon1, lat1, lon2, lat2, n_intermediate)
            densified_coords.extend(zip(lons, lats))
        
        densified_coords.append((lon2, lat2))
    
    transformed_coords = [transformer.transform(lon, lat) for lon, lat in densified_coords]
    
    return LineString(transformed_coords)