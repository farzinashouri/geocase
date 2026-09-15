"""Convert shapely geometries in an arbitrary CRS to RFC 7946 compliant GeoJSON geometry dicts."""

from pyproj import Transformer
from shapely.geometry import mapping
from shapely.geometry.polygon import orient
from shapely.ops import transform as shapely_transform

_WGS84_EPSG = 4326


def _reproject(geom, epsg):
    if epsg == _WGS84_EPSG:
        return geom
    transformer = Transformer.from_crs(f"EPSG:{epsg}", f"EPSG:{_WGS84_EPSG}", always_xy=True)
    return shapely_transform(transformer.transform, geom)


def _fix_orientation(geom):
    geom_type = geom.geom_type
    if geom_type == "Polygon":
        return orient(geom, sign=1.0)
    if geom_type == "MultiPolygon":
        return type(geom)([orient(poly, sign=1.0) for poly in geom.geoms])
    if geom_type == "GeometryCollection":
        return type(geom)([_fix_orientation(g) for g in geom.geoms])
    return geom


def _strip_z(coords):
    if isinstance(coords[0], (int, float)):
        return list(coords[:2])
    return [_strip_z(c) for c in coords]


def _drop_z_dim(mapping_dict):
    if mapping_dict["type"] == "GeometryCollection":
        mapping_dict["geometries"] = [_drop_z_dim(g) for g in mapping_dict["geometries"]]
        return mapping_dict
    mapping_dict["coordinates"] = _strip_z(mapping_dict["coordinates"])
    return mapping_dict


def to_rfc7946(geom, epsg):
    """Return an RFC 7946 compliant GeoJSON geometry dict for a shapely geometry in the given EPSG CRS."""
    reprojected = _reproject(geom, epsg)
    oriented = _fix_orientation(reprojected)
    geojson = mapping(oriented)
    geojson = _drop_z_dim(geojson)
    return geojson