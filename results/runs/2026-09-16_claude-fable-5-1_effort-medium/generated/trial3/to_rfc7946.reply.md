```python
"""Convert shapely geometries to RFC 7946-compliant GeoJSON geometry dicts.

RFC 7946 requires:
  * coordinates in WGS 84 (EPSG:4326), ordered longitude, latitude[, altitude];
  * positions of at most three elements (M values are dropped);
  * polygon rings that are closed, exterior counterclockwise, holes clockwise;
  * only the seven GeoJSON geometry types (LinearRing becomes LineString);
  * finite numbers only (JSON has no NaN/Infinity).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

_WGS84 = 4326


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    """Reproject horizontal coordinates to WGS 84 (lon/lat); keep Z untouched."""
    if int(epsg) == _WGS84:
        return geom
    transformer = Transformer.from_crs(f"EPSG:{int(epsg)}", f"EPSG:{_WGS84}", always_xy=True)

    def _func(coords: np.ndarray) -> np.ndarray:
        if coords.size == 0:
            return coords
        lon, lat = transformer.transform(coords[:, 0], coords[:, 1])
        out = np.array(coords, dtype=float, copy=True)
        out[:, 0] = lon
        out[:, 1] = lat
        return out

    return shapely.transform(geom, _func, include_z=bool(geom.has_z))


def _orient(geom: BaseGeometry) -> BaseGeometry:
    """Apply the right-hand rule (exterior CCW, interiors CW) to every polygon."""
    t = geom.geom_type
    if t == "Polygon":
        return geom if geom.is_empty else orient(geom, sign=1.0)
    if t == "MultiPolygon":
        return shapely.MultiPolygon([_orient(p) for p in geom.geoms])
    if t == "GeometryCollection":
        return shapely.GeometryCollection([_orient(g) for g in geom.geoms])
    return geom


def _position(coord) -> list[float]:
    pos = [float(v) for v in coord[:3]]  # lon, lat[, alt]; drop M and beyond
    for v in pos:
        if not math.isfinite(v):
            raise ValueError(f"non-finite coordinate value in geometry: {v!r}")
    return pos


def _positions(seq) -> list[list[float]]:
    return [_position(c) for c in seq]


def _polygon_coords(poly) -> list[list[list[float]]]:
    if poly.is_empty:
        return []
    return [_positions(poly.exterior.coords)] + [_positions(r.coords) for r in poly.interiors]


def _encode(geom: BaseGeometry) -> dict[str, Any]:
    t = geom.geom_type
    if t == "Point":
        return {"type": "Point", "coordinates": [] if geom.is_empty else _position(geom.coords[0])}
    if t in ("LineString", "LinearRing"):
        return {"type": "LineString", "coordinates": _positions(geom.coords)}
    if t == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon_coords(geom)}
    if t == "MultiPoint":
        return {"type": "MultiPoint", "coordinates": [_position(p.coords[0]) for p in geom.geoms if not p.is_empty]}
    if t == "MultiLineString":
        return {"type": "MultiLineString", "coordinates": [_positions(l.coords) for l in geom.geoms]}
    if t == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [_polygon_coords(p) for p in geom.geoms]}
    if t == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": [_encode(g) for g in geom.geoms]}
    raise TypeError(f"unsupported geometry type: {t}")


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict[str, Any]:
    """Return ``geom`` (whose coordinates are in EPSG ``epsg``) as an RFC 7946 GeoJSON geometry dict."""
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    geom = _reproject(geom, epsg)
    geom = _orient(geom)
    return _encode(geom)
```