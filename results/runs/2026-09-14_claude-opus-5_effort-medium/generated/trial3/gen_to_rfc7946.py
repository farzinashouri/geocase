"""Convert shapely geometries into RFC 7946 (GeoJSON) geometry objects.

RFC 7946 pins GeoJSON to a single CRS -- WGS 84 longitude/latitude
(EPSG:4326, decimal degrees) -- so this module reprojects from whatever
EPSG the input coordinates are in.  Input coordinates are always read in
"x, y" order (easting/longitude first), matching shapely's convention and
pyproj's ``always_xy=True``.

The module implements the RFC's MUST-level rules: WGS 84 output, closed
linear rings, and the right-hand rule (exterior rings counterclockwise,
interior rings clockwise).  Antimeridian cutting is only a SHOULD in the
RFC and is not performed; a geometry that crosses +/-180 degrees is emitted
with its positions unmodified.  Any M values are dropped, since RFC 7946
positions carry at most x, y, z.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Dict, List, Sequence

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84_EPSG = 4326

# Tolerance for snapping coordinates that land just outside the valid
# lon/lat domain because of floating-point error in the projection.
_DEGREE_EPS = 1e-9

_SIMPLE_TYPES = {
    "Point": "Point",
    "LineString": "LineString",
    "LinearRing": "LineString",  # not a GeoJSON type; degrade to LineString
    "Polygon": "Polygon",
    "MultiPoint": "MultiPoint",
    "MultiLineString": "MultiLineString",
    "MultiPolygon": "MultiPolygon",
}

Position = List[float]


@lru_cache(maxsize=64)
def _transformer(epsg: int) -> Transformer:
    """Cached source-EPSG -> WGS 84 transformer."""
    return Transformer.from_crs(
        CRS.from_epsg(epsg), CRS.from_epsg(_WGS84_EPSG), always_xy=True
    )


def _clean(value: float) -> float:
    """Return a JSON-safe float, collapsing -0.0 to 0.0."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("coordinates must be finite; JSON has no NaN/Infinity")
    return 0.0 if value == 0.0 else value


def _normalize_lon(lon: float) -> float:
    lon = _clean(lon)
    if -180.0 <= lon <= 180.0:
        return lon
    # Wrap into [-180, 180], keeping an exact +180 as +180.
    wrapped = math.remainder(lon, 360.0)
    return 0.0 if wrapped == 0.0 else wrapped


def _normalize_lat(lat: float) -> float:
    lat = _clean(lat)
    if lat > 90.0:
        if lat - 90.0 > _DEGREE_EPS:
            raise ValueError(f"latitude {lat} is outside [-90, 90]")
        return 90.0
    if lat < -90.0:
        if -90.0 - lat > _DEGREE_EPS:
            raise ValueError(f"latitude {lat} is outside [-90, 90]")
        return -90.0
    return lat


def _positions(geom: BaseGeometry, epsg: int) -> List[Position]:
    """Project one coordinate sequence into RFC 7946 positions."""
    coords = shapely.get_coordinates(geom, include_z=True)
    if coords.size == 0:
        return []

    xs = coords[:, 0]
    ys = coords[:, 1]
    zs = coords[:, 2] if coords.shape[1] > 2 else np.full(len(coords), np.nan)

    if epsg == _WGS84_EPSG:
        lons, lats = xs, ys
    else:
        lons, lats = _transformer(epsg).transform(xs, ys)

    out: List[Position] = []
    for lon, lat, z in zip(np.atleast_1d(lons), np.atleast_1d(lats), zs):
        position = [_normalize_lon(lon), _normalize_lat(lat)]
        if not np.isnan(z):
            position.append(_clean(z))
        out.append(position)
    return out


def _signed_area(ring: Sequence[Position]) -> float:
    """Shoelace area in the lon/lat plane; positive means counterclockwise."""
    total = 0.0
    for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _ring(ring_geom: BaseGeometry, epsg: int, *, ccw: bool) -> List[Position]:
    """Project a linear ring, close it, and orient it per the right-hand rule."""
    positions = _positions(ring_geom, epsg)
    if not positions:
        raise ValueError("polygon rings must not be empty")

    # Reprojection can perturb the closing position; force exact closure.
    if positions[0] != positions[-1]:
        positions.append(list(positions[0]))
    else:
        positions[-1] = list(positions[0])

    if len(positions) < 4:
        raise ValueError("a linear ring needs at least four positions")

    area = _signed_area(positions)
    if (area > 0.0) != ccw and area != 0.0:
        positions.reverse()
    return positions


def _polygon_coordinates(polygon: BaseGeometry, epsg: int) -> List[List[Position]]:
    rings = [_ring(polygon.exterior, epsg, ccw=True)]
    rings.extend(_ring(interior, epsg, ccw=False) for interior in polygon.interiors)
    return rings


def _coordinates(geom: BaseGeometry, epsg: int) -> Any:
    geom_type = geom.geom_type

    if geom_type == "Point":
        positions = _positions(geom, epsg)
        if not positions:
            raise ValueError("an empty Point has no RFC 7946 representation")
        return positions[0]

    if geom_type in ("LineString", "LinearRing"):
        positions = _positions(geom, epsg)
        if len(positions) < 2:
            raise ValueError("a LineString needs at least two positions")
        return positions

    if geom_type == "Polygon":
        if geom.is_empty:
            raise ValueError("an empty Polygon has no RFC 7946 representation")
        return _polygon_coordinates(geom, epsg)

    if geom_type == "MultiPoint":
        return _positions(geom, epsg)

    if geom_type == "MultiLineString":
        return [_coordinates(part, epsg) for part in geom.geoms]

    if geom_type == "MultiPolygon":
        return [_polygon_coordinates(part, epsg) for part in geom.geoms]

    raise ValueError(f"unsupported geometry type: {geom_type!r}")


def _flatten_collection(geom: BaseGeometry, epsg: int) -> List[Dict[str, Any]]:
    """Build a flat list of geometry objects; the RFC discourages nesting."""
    members: List[Dict[str, Any]] = []
    for part in geom.geoms:
        if part.geom_type == "GeometryCollection":
            members.extend(_flatten_collection(part, epsg))
        else:
            members.append(to_rfc7946(part, epsg))
    return members


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are in the CRS given by ``epsg``,
        in x/y (longitude/latitude or easting/northing) order.
    epsg:
        Integer EPSG code of that CRS, e.g. ``4326`` or ``3857``.

    Returns
    -------
    dict
        A JSON-serializable GeoJSON geometry object with WGS 84 coordinates.
        ``GeometryCollection`` inputs yield a ``geometries`` member instead of
        ``coordinates``, as the RFC requires.

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry or ``epsg`` is not an integer.
    ValueError
        If ``epsg`` is not a usable EPSG code, or the geometry cannot be
        expressed under RFC 7946 (for example an empty ``Point``).
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, (int, np.integer)):
        raise TypeError("epsg must be an integer EPSG code")
    epsg = int(epsg)
    if epsg <= 0:
        raise ValueError(f"invalid EPSG code: {epsg}")

    if epsg != _WGS84_EPSG:
        try:
            _transformer(epsg)
        except Exception as exc:  # unknown code, or no path to WGS 84
            raise ValueError(f"cannot transform EPSG:{epsg} to EPSG:4326: {exc}") from exc

    if geom.geom_type == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": _flatten_collection(geom, epsg)}

    try:
        geojson_type = _SIMPLE_TYPES[geom.geom_type]
    except KeyError:
        raise ValueError(f"unsupported geometry type: {geom.geom_type!r}") from None

    return {"type": geojson_type, "coordinates": _coordinates(geom, epsg)}