```python
"""Convert shapely geometries in an arbitrary CRS to RFC 7946 compliant GeoJSON geometry dicts."""

from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.geometry.collection import GeometryCollection
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import transform as shapely_transform


def _orient_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Apply the RFC 7946 right-hand rule (CCW exterior rings, CW holes)."""
    gtype = geom.geom_type
    if gtype == "Polygon":
        return orient(geom, sign=1.0)
    if gtype == "MultiPolygon":
        return MultiPolygon([orient(part, sign=1.0) for part in geom.geoms])
    if gtype == "GeometryCollection":
        return GeometryCollection([_orient_geometry(part) for part in geom.geoms])
    return geom


def _to_jsonable(coords: Any) -> Any:
    if isinstance(coords, (int, float)):
        return coords
    return [_to_jsonable(c) for c in coords]


def _mapping_to_geojson(m: dict) -> dict:
    if m["type"] == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_mapping_to_geojson(g) for g in m["geometries"]],
        }
    return {"type": m["type"], "coordinates": _to_jsonable(m["coordinates"])}


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    """Return `geom` (given in the CRS identified by `epsg`) as an RFC 7946
    GeoJSON geometry dict, i.e. reprojected to WGS84 with longitude/latitude
    axis order and right-hand-rule polygon winding."""
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    projected = shapely_transform(transformer.transform, geom)
    oriented = _orient_geometry(projected)
    return _mapping_to_geojson(mapping(oriented))
```