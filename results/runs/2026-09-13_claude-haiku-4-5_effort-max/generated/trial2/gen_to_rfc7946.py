from shapely.geometry import mapping
from shapely.ops import transform
import pyproj


def to_rfc7946(geom, epsg):
    """
    Convert a shapely geometry from any EPSG CRS to RFC 7946 compliant GeoJSON.
    
    Args:
        geom: A shapely geometry object
        epsg: Integer EPSG code of the geometry's coordinate reference system
    
    Returns:
        A dict representing a valid RFC 7946 GeoJSON geometry object
    """
    transformer = pyproj.Transformer.from_epsg(epsg, 4326, always_xy=True)
    transformed_geom = transform(transformer.transform, geom)
    return mapping(transformed_geom)