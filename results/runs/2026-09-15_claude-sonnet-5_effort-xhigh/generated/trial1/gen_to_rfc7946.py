from __future__ import annotations

from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from pyproj import CRS, Transformer

_WGS84 = CRS.from_epsg(4326)


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    src_crs = CRS.from_epsg(epsg)
    if src_crs != _WGS84:
        # always_xy=True forces (lon, lat) GIS order on both ends, regardless
        # of the authority-defined axis order of the source or target CRS.
        transformer = Transformer.from_crs(src_crs, _WGS84, always_xy=True)
        geom = shapely_transform(transformer.transform, geom)
    return _to_geojson_dict(mapping(geom))


def _to_geojson_dict(gj: dict) -> dict:
    geom_type = "LineString" if gj["type"] == "LinearRing" else gj["type"]
    result = {"type": geom_type}
    if geom_type == "GeometryCollection":
        result["geometries"] = [_to_geojson_dict(g) for g in gj["geometries"]]
        return result
    coords = _nested_list(gj["coordinates"])
    if geom_type == "Polygon":
        coords = _oriented_rings(coords)
    elif geom_type == "MultiPolygon":
        coords = [_oriented_rings(rings) for rings in coords]
    result["coordinates"] = coords
    return result


def _nested_list(coords):
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (int, float)):
            return [float(c) for c in coords]
        return [_nested_list(c) for c in coords]
    return float(coords)


def _oriented_rings(rings: list) -> list:
    oriented = []
    for i, ring in enumerate(rings):
        area = _signed_area(ring)
        is_hole = i > 0
        if (is_hole and area > 0) or (not is_hole and area < 0):
            ring = list(reversed(ring))
        oriented.append(ring)
    return oriented


def _signed_area(ring: list) -> float:
    total = 0.0
    for (x1, y1, *_r1), (x2, y2, *_r2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0