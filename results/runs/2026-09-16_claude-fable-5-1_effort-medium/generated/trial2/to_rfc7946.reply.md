Here is the module.

```python
"""Convert shapely geometries to RFC 7946 (GeoJSON) geometry dicts."""

from __future__ import annotations

from typing import Any

import shapely
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

_WGS84 = 4326


def _transformer(epsg: int) -> Transformer:
    return Transformer.from_crs(f"EPSG:{int(epsg)}", f"EPSG:{_WGS84}", always_xy=True)


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    if int(epsg) == _WGS84:
        return geom
    t = _transformer(epsg)

    def fn(coords):
        x, y = t.transform(coords[:, 0], coords[:, 1])
        out = coords.astype(float).copy()
        out[:, 0] = x
        out[:, 1] = y
        return out

    return shapely.transform(geom, fn, include_z=True)


def _strip_m(geom: BaseGeometry) -> BaseGeometry:
    if getattr(geom, "has_m", False):
        geom = shapely.force_3d(geom) if geom.has_z else shapely.force_2d(geom)
    return geom


def _orient(geom: BaseGeometry) -> BaseGeometry:
    gt = geom.geom_type
    if gt == "Polygon":
        return orient(geom, 1.0)
    if gt == "MultiPolygon":
        return shapely.MultiPolygon([orient(p, 1.0) for p in geom.geoms])
    if gt == "GeometryCollection":
        return shapely.GeometryCollection([_orient(g) for g in geom.geoms])
    return geom


def _pos(c) -> list[float]:
    return [float(v) for v in c]


def _coords(geom: BaseGeometry) -> Any:
    gt = geom.geom_type
    if geom.is_empty:
        return []
    if gt == "Point":
        return _pos(geom.coords[0])
    if gt in ("LineString", "LinearRing"):
        return [_pos(c) for c in geom.coords]
    if gt == "Polygon":
        rings = [geom.exterior, *geom.interiors]
        return [[_pos(c) for c in r.coords] for r in rings]
    if gt in ("MultiPoint", "MultiLineString", "MultiPolygon"):
        return [_coords(g) for g in geom.geoms]
    raise TypeError(f"Unsupported geometry type: {gt}")


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    """Return ``geom`` (in CRS ``epsg``) as an RFC 7946 GeoJSON geometry dict.

    Coordinates are reprojected to WGS 84 longitude/latitude, M values are
    dropped, and polygon rings follow the right-hand rule (exterior
    counterclockwise, holes clockwise).
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    g = _orient(_reproject(_strip_m(geom), epsg))
    gt = g.geom_type
    if gt == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [to_rfc7946(part, _WGS84) for part in g.geoms],
        }
    if gt == "LinearRing":
        gt = "LineString"
    return {"type": gt, "coordinates": _coords(g)}
```