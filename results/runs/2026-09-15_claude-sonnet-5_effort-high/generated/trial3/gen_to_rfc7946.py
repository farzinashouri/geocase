"""Convert shapely geometries into RFC 7946 conformant GeoJSON geometry dicts."""

from __future__ import annotations

from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import GeometryCollection, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import transform as shapely_transform


def _reorient(geom: BaseGeometry) -> BaseGeometry:
    """Apply the RFC 7946 right-hand winding rule to polygonal geometries."""
    gtype = geom.geom_type
    if gtype == "Polygon":
        return orient(geom, sign=1.0)
    if gtype == "MultiPolygon":
        return MultiPolygon([orient(p, sign=1.0) for p in geom.geoms])
    if gtype == "GeometryCollection":
        return GeometryCollection([_reorient(g) for g in geom.geoms])
    return geom


def _to_lists(obj: Any) -> Any:
    if isinstance(obj, (list, tuple)):
        return [_to_lists(item) for item in obj]
    return obj


def _mapping_to_dict(mapping: dict) -> dict:
    if mapping["type"] == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_mapping_to_dict(g) for g in mapping["geometries"]],
        }
    return {"type": mapping["type"], "coordinates": _to_lists(mapping["coordinates"])}


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    """Convert ``geom`` (in the CRS identified by ``epsg``) to an RFC 7946 GeoJSON geometry dict.

    The result is reprojected to WGS84 longitude/latitude (as RFC 7946 mandates)
    and has polygon rings wound per the right-hand rule.
    """
    src_crs = CRS.from_epsg(epsg)
    dst_crs = CRS.from_epsg(4326)

    if src_crs != dst_crs:
        transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        geom = shapely_transform(transformer.transform, geom)

    geom = _reorient(geom)

    return _mapping_to_dict(geom.__geo_interface__)