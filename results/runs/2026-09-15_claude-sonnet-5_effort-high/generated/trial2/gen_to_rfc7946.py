"""Convert shapely geometries into RFC 7946 compliant GeoJSON geometry dicts."""
from __future__ import annotations

from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as _shapely_transform

_WGS84 = CRS.from_epsg(4326)


def _round_coords(coords: Any) -> Any:
    if not coords:
        return list(coords)
    if isinstance(coords[0], (int, float)):
        return [round(float(v), 9) for v in coords]
    return [_round_coords(c) for c in coords]


def _build(mapped: dict) -> dict:
    if mapped["type"] == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_build(g) for g in mapped["geometries"]],
        }
    return {
        "type": mapped["type"],
        "coordinates": _round_coords(mapped["coordinates"]),
    }


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    """Return `geom` (in the CRS identified by `epsg`) as an RFC 7946 GeoJSON geometry dict."""
    src_crs = CRS.from_epsg(epsg)

    if src_crs != _WGS84:
        transformer = Transformer.from_crs(src_crs, _WGS84, always_xy=True)
        geom = _shapely_transform(transformer.transform, geom)

    return _build(mapping(geom))