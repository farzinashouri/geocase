from pyproj import CRS, Transformer
from shapely.ops import transform
from shapely import mapping


def to_rfc7946(geom, epsg):
    """Convert a shapely geometry to RFC 7946 GeoJSON geometry object."""
    src_crs = CRS.from_epsg(epsg)
    dst_crs = CRS.from_epsg(4326)
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    geom_wgs84 = transform(transformer.transform, geom)
    return mapping(geom_wgs84)