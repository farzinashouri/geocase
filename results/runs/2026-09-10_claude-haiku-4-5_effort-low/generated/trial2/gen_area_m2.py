from shapely.ops import transform
from pyproj import Transformer

def area_m2(geom):
    transformer = Transformer.from_crs("EPSG:4326", "+proj=moll +ellps=WGS84", always_xy=True)
    def proj(x, y, z=None):
        return transformer.transform(x, y, z) if z is not None else transformer.transform(x, y)
    return float(transform(proj, geom).area)