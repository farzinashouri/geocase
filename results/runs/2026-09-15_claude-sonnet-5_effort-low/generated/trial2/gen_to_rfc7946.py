"""Convert shapely geometries to RFC 7946 compliant GeoJSON geometry dicts."""

from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
    mapping,
)
from shapely.geometry.polygon import orient
from shapely.ops import transform
from pyproj import Transformer, CRS


def _to_wgs84(geom, epsg):
    src_crs = CRS.from_epsg(epsg)
    dst_crs = CRS.from_epsg(4326)
    if src_crs.equals(dst_crs):
        return geom
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    return transform(lambda x, y, z=None: transformer.transform(x, y), geom)


def _orient_polygon(poly):
    # RFC 7946: exterior rings counterclockwise, interior rings clockwise.
    return orient(poly, sign=1.0)


def _fix_winding(geom):
    if isinstance(geom, Polygon):
        return _orient_polygon(geom)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([_orient_polygon(p) for p in geom.geoms])
    if isinstance(geom, GeometryCollection):
        return GeometryCollection([_fix_winding(g) for g in geom.geoms])
    return geom


def _strip_z(geom):
    if not geom.has_z:
        return geom

    def _drop_z(x, y, z=None):
        return (x, y)

    return transform(_drop_z, geom)


def to_rfc7946(geom, epsg):
    """Convert a shapely geometry in the given EPSG CRS to an RFC 7946 GeoJSON
    geometry dict (reprojected to WGS84, with polygon winding order enforced).
    """
    wgs84_geom = _to_wgs84(geom, epsg)
    wgs84_geom = _strip_z(wgs84_geom)
    wgs84_geom = _fix_winding(wgs84_geom)
    return dict(mapping(wgs84_geom))