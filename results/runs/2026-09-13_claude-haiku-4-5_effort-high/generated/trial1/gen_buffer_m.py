from shapely.ops import transform as shapely_transform
from pyproj import CRS, Transformer


def buffer_m(geom, distance_m):
    """
    Buffer a WGS84 geometry by a distance in meters.
    
    Uses azimuthal equidistant projection centered on the geometry's
    centroid to accurately preserve distances.
    """
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y
    
    # Azimuthal equidistant projection centered on centroid
    wgs84 = CRS.from_epsg(4326)
    aeqd = CRS.from_proj4(f"+proj=aeqd +lon_0={lon0} +lat_0={lat0} +datum=WGS84")
    
    to_aeqd = Transformer.from_crs(wgs84, aeqd, always_xy=True)
    from_aeqd = Transformer.from_crs(aeqd, wgs84, always_xy=True)
    
    def to_aeqd_fn(x, y, z=None):
        x_t, y_t = to_aeqd.transform(x, y)
        return (x_t, y_t, z) if z is not None else (x_t, y_t)
    
    def from_aeqd_fn(x, y, z=None):
        x_t, y_t = from_aeqd.transform(x, y)
        return (x_t, y_t, z) if z is not None else (x_t, y_t)
    
    geom_aeqd = shapely_transform(to_aeqd_fn, geom)
    geom_buffered = geom_aeqd.buffer(distance_m)
    return shapely_transform(from_aeqd_fn, geom_buffered)