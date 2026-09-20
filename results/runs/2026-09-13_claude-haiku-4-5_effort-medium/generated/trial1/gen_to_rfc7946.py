import shapely.ops
from pyproj import Transformer

def to_rfc7946(geom, epsg):
    if epsg != 4326:
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        geom = shapely.ops.transform(transformer.transform, geom)
    
    return geom.__geo_interface__