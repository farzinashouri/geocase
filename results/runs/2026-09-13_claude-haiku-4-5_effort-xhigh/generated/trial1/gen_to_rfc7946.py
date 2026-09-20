from shapely.ops import transform
from pyproj import Transformer

def to_rfc7946(geom, epsg):
    if epsg != 4326:
        transformer = Transformer.from_epsg(epsg, 4326, always_xy=True)
        
        def transform_coord(x, y, z=None):
            x2, y2 = transformer.transform(x, y)
            return (x2, y2, z) if z is not None else (x2, y2)
        
        geom = transform(transform_coord, geom)
    
    return geom.__geo_interface__