"""Convert shapely geometries to RFC 7946 (GeoJSON) geometry objects.

The single public function is :func:`to_rfc7946`.  It reprojects the input
geometry from the given EPSG code to WGS 84 (longitude, latitude order, as
RFC 7946 section 4 requires), enforces the right-hand rule for polygon
rings (section 3.1.6), and emits a plain ``dict`` containing only the
``type`` and ``coordinates`` members (or ``geometries`` for a
GeometryCollection).  No ``crs`` member is ever emitted.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

from pyproj import CRS, Transformer
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

__all__ = ["to_rfc7946"]

_WGS84_EPSG = 4326


def _transformer(epsg: int) -> Transformer:
    """Build a transformer from ``epsg`` to WGS 84 with (x, y) = (lon, lat) order."""
    src = CRS.from_epsg(int(epsg))
    dst = CRS.from_epsg(_WGS84_EPSG)
    return Transformer.from_crs(src, dst, always_xy=True)


def _clean(value: float) -> float:
    """Return a plain Python float; reject non-finite values (RFC 7946 needs JSON numbers)."""
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("Reprojection produced a non-finite coordinate; "
                         "the geometry is outside the valid area of the source CRS.")
    return out


def _positions(coords: Sequence[Sequence[float]], tf: Transformer) -> List[List[float]]:
    """Reproject a sequence of coordinate tuples into GeoJSON positions."""
    out: List[List[float]] = []
    for c in coords:
        if len(c) >= 3:
            x, y, z = tf.transform(c[0], c[1], c[2])
            out.append([_clean(x), _clean(y), _clean(z)])
        else:
            x, y = tf.transform(c[0], c[1])
            out.append([_clean(x), _clean(y)])
    return out


def _point(geom: Point, tf: Transformer) -> Dict[str, Any]:
    if geom.is_empty:
        return {"type": "Point", "coordinates": []}
    return {"type": "Point", "coordinates": _positions([geom.coords[0]], tf)[0]}


def _linestring(geom: LineString, tf: Transformer) -> Dict[str, Any]:
    # LinearRing is a shapely-only type; RFC 7946 has no such type, so it is
    # emitted as a closed LineString.
    if geom.is_empty:
        return {"type": "LineString", "coordinates": []}
    return {"type": "LineString", "coordinates": _positions(list(geom.coords), tf)}


def _polygon(geom: Polygon, tf: Transformer) -> Dict[str, Any]:
    if geom.is_empty:
        return {"type": "Polygon", "coordinates": []}
    # Reproject each ring first, then orient in the target CRS so that the
    # right-hand rule (exterior counterclockwise, holes clockwise) holds in
    # lon/lat space regardless of how the source projection was handed.
    rings = [_positions(list(geom.exterior.coords), tf)]
    rings.extend(_positions(list(ring.coords), tf) for ring in geom.interiors)
    reprojected = Polygon(rings[0], rings[1:])
    oriented = orient(reprojected, sign=1.0)
    coords = [[[_clean(v) for v in pos] for pos in oriented.exterior.coords]]
    coords.extend([[_clean(v) for v in pos] for pos in ring.coords]
                  for ring in oriented.interiors)
    return {"type": "Polygon", "coordinates": coords}


def _multipoint(geom: MultiPoint, tf: Transformer) -> Dict[str, Any]:
    return {"type": "MultiPoint",
            "coordinates": [_point(p, tf)["coordinates"] for p in geom.geoms if not p.is_empty]}


def _multilinestring(geom: MultiLineString, tf: Transformer) -> Dict[str, Any]:
    return {"type": "MultiLineString",
            "coordinates": [_linestring(l, tf)["coordinates"] for l in geom.geoms if not l.is_empty]}


def _multipolygon(geom: MultiPolygon, tf: Transformer) -> Dict[str, Any]:
    return {"type": "MultiPolygon",
            "coordinates": [_polygon(p, tf)["coordinates"] for p in geom.geoms if not p.is_empty]}


def _collection(geom: GeometryCollection, tf: Transformer) -> Dict[str, Any]:
    return {"type": "GeometryCollection",
            "geometries": [_convert(g, tf) for g in geom.geoms]}


def _convert(geom: BaseGeometry, tf: Transformer) -> Dict[str, Any]:
    if isinstance(geom, Point):
        return _point(geom, tf)
    if isinstance(geom, (LineString, LinearRing)):
        return _linestring(geom, tf)
    if isinstance(geom, Polygon):
        return _polygon(geom, tf)
    if isinstance(geom, MultiPoint):
        return _multipoint(geom, tf)
    if isinstance(geom, MultiLineString):
        return _multilinestring(geom, tf)
    if isinstance(geom, MultiPolygon):
        return _multipolygon(geom, tf)
    if isinstance(geom, GeometryCollection):
        return _collection(geom, tf)
    raise TypeError(f"Unsupported geometry type: {type(geom).__name__}")


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` (whose coordinates are in EPSG:``epsg``) as an RFC 7946 geometry dict.

    Coordinates are reprojected to WGS 84 and emitted as ``[longitude,
    latitude]`` or ``[longitude, latitude, altitude]`` positions.  Polygon
    rings follow the right-hand rule.  Only ``type`` and ``coordinates``
    (or ``geometries``) are present; no ``crs`` member is emitted.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    return _convert(geom, _transformer(epsg))