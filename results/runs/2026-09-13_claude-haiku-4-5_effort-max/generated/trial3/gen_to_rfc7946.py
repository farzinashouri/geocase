from shapely.geometry import mapping
from shapely import ops
import pyproj


def to_rfc7946(geom, epsg):
    """
    Convert a shapely geometry to RFC 7946 GeoJSON geometry object.
    
    Transforms the geometry from its source CRS to WGS84 (EPSG:4326)
    and returns a valid GeoJSON geometry dict with 'type' and 'coordinates'.
    
    Args:
        geom: A shapely geometry object
        epsg: Integer EPSG code of the geometry's source CRS
    
    Returns:
        A dict with 'type' and 'coordinates' members
    """
    if epsg != 4326:
        source_crs = pyproj.CRS.from_epsg(epsg)
        target_crs = pyproj.CRS.from_epsg(4326)
        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
        geom = ops.transform(transformer.transform, geom)
    
    geojson = mapping(geom)
    return {
        'type': geojson['type'],
        'coordinates': geojson['coordinates']
    }