from shapely.geometry import LineString
from pyproj import Geod, CRS, Transformer

def project_line(line, dst_epsg):
    """Project a WGS84 LineString to a projected CRS via geodesic densification."""
    coords = list(line.coords)
    
    if not coords:
        return LineString()
    
    src_crs = CRS.from_epsg(4326)
    dst_crs = CRS.from_epsg(dst_epsg)
    geod = Geod(ellps='WGS84')
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    
    densified_coords = []
    segment_spacing = 25000
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        npts = max(2, (distance + segment_spacing - 1) // segment_spacing + 1)
        lons, lats = geod.npts(lon1, lat1, lon2, lat2, npts)
        
        for lon, lat in zip(lons[:-1], lats[:-1]):
            densified_coords.append((lon, lat))
    
    densified_coords.append(coords[-1])
    transformed_coords = [transformer.transform(lon, lat) for lon, lat in densified_coords]
    return LineString(transformed_coords)