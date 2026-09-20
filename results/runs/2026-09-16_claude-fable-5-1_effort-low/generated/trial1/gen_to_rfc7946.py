"""Convert a shapely geometry in any EPSG CRS to an RFC 7946 GeoJSON geometry dict.

RFC 7946 requires:
  * coordinates in WGS 84 (EPSG:4326), ordered longitude, latitude[, altitude];
  * polygon rings following the right-hand rule (exterior counter-clockwise,
    holes clockwise) and closed with at least four positions;
  * positions with at most three elements (any M measure is dropped);
  * empty geometries expressed with an empty ``coordinates`` array.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

_WGS84 = 4326


@lru_cache(maxsize=64)
def _transformer(epsg: int) -> Transformer:
    return Transformer.from_crs(f"EPSG:{epsg}", f"EPSG:{_WGS84}", always_xy=True)


def _to_wgs84(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    has_z = bool(geom.has_z)
    if epsg == _WGS84:
        # Drop any M dimension while keeping Z; shapely.transform re-emits
        # only the requested dimensions.
        return shapely.transform(geom, lambda c: c, include_z=has_z)

    transformer = _transformer(epsg)

    def project(coords: np.ndarray) -> np.ndarray:
        out = np.array(coords, dtype=float, copy=True)
        lon, lat = transformer.transform(out[:, 0], out[:, 1])
        out[:, 0] = lon
        out[:, 1] = lat
        return out

    return shapely.transform(geom, project, include_z=has_z)


def _normalize_lon(lon: float) -> float:
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    return wrapped


def _positions(g: BaseGeometry, has_z: bool) -> list[list[float]]:
    arr = shapely.get_coordinates(g, include_z=has_z)
    result: list[list[float]] = []
    for row in arr.tolist():
        pos = [float(v) for v in row[: 3 if has_z else 2]]
        if not all(math.isfinite(v) for v in pos):
            raise ValueError(f"non-finite coordinate after reprojection: {pos}")
        pos[0] = _normalize_lon(pos[0])
        result.append(pos)
    return result


def _polygon_rings(poly: BaseGeometry, has_z: bool) -> list[list[list[float]]]:
    if poly.is_empty:
        return []
    poly = orient(poly, sign=1.0)  # exterior CCW, interiors CW (RFC 7946 §3.1.6)
    rings = [_positions(poly.exterior, has_z)]
    rings.extend(_positions(ring, has_z) for ring in poly.interiors)
    return rings


def _encode(geom: BaseGeometry, has_z: bool) -> dict[str, Any]:
    kind = geom.geom_type

    if kind == "Point":
        pts = _positions(geom, has_z)
        return {"type": "Point", "coordinates": pts[0] if pts else []}

    if kind in ("LineString", "LinearRing"):
        return {"type": "LineString", "coordinates": _positions(geom, has_z)}

    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon_rings(geom, has_z)}

    if kind == "MultiPoint":
        coords = [p for part in geom.geoms for p in _positions(part, has_z)]
        return {"type": "MultiPoint", "coordinates": coords}

    if kind == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [_positions(part, has_z) for part in geom.geoms if not part.is_empty],
        }

    if kind == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [_polygon_rings(part, has_z) for part in geom.geoms if not part.is_empty],
        }

    if kind == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_encode(part, has_z) for part in geom.geoms],
        }

    raise TypeError(f"unsupported geometry type: {kind}")


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict[str, Any]:
    """Return ``geom`` (whose coordinates are in ``EPSG:<epsg>``) as an
    RFC 7946 GeoJSON geometry object (a plain ``dict``)."""
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    epsg = int(epsg)
    wgs = _to_wgs84(geom, epsg)
    return _encode(wgs, bool(wgs.has_z))


__all__ = ["to_rfc7946"]