"""Convert shapely geometries to RFC 7946 conformant GeoJSON geometry dicts."""

from __future__ import annotations

from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    if epsg == 4326:
        return geom
    transformer = Transformer.from_crs(CRS.from_epsg(epsg), _WGS84, always_xy=True)
    return transform(transformer.transform, geom)


def _right_hand_rule(geom: BaseGeometry) -> BaseGeometry:
    """Reorder polygon rings per RFC 7946 3.1.6: exterior CCW, holes CW."""
    if isinstance(geom, Polygon):
        return orient(geom, sign=1.0)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([orient(p, sign=1.0) for p in geom.geoms])
    if isinstance(geom, GeometryCollection):
        return GeometryCollection([_right_hand_rule(g) for g in geom.geoms])
    return geom


def _to_lists(obj: Any) -> Any:
    if isinstance(obj, (list, tuple)):
        return [_to_lists(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _to_lists(value) for key, value in obj.items()}
    return obj


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict[str, Any]:
    """Convert ``geom`` (in CRS ``epsg``) into an RFC 7946 GeoJSON geometry dict."""
    wgs84_geom = _reproject(geom, epsg)
    oriented = _right_hand_rule(wgs84_geom)
    return _to_lists(mapping(oriented))