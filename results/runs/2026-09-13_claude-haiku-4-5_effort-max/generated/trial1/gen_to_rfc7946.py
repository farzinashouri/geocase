from shapely.geometry import mapping
from shapely.ops import transform
from pyproj import Transformer


def to_rfc7946(geom, epsg):
    transformer = Transformer.from_epsg(epsg, 4326, always_xy=True)
    transformed = transform(transformer.transform, geom)
    geojson = mapping(transformed)
    
    result = {'type': geojson['type']}
    if 'coordinates' in geojson:
        result['coordinates'] = geojson['coordinates']
    elif 'geometries' in geojson:
        result['geometries'] = geojson['geometries']
    
    return result