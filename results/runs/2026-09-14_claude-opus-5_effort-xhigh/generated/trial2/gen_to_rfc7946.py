"""Strict RFC 7946 (GeoJSON) encoding of shapely geometries.

The single public entry point is :func:`to_rfc7946`.  Importing this module has
no side effects: no I/O, no logging or warning configuration, no PROJ or GEOS
objects built at import time.
"""

from __future__ import annotations

import math
from functools import lru_cache
from numbers import Integral
from typing import Any, Dict, List

import numpy as np
import shapely
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely.affinity import translate
from shapely.errors import GEOSException
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84 = 4326
_LAT_LIMIT = 90.0
_LON_LIMIT = 180.0
_PERIOD = 360.0
_LAT_TOL = 1e-7  # round-off slack at the poles before an error is raised

_SIMPLE_TYPES = frozenset(
    {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}
)
# A Point needs one position and a LineString at least two (RFC 7946 §3.1.2,
# §3.1.4), so emptiness cannot be expressed for either.
_UNREPRESENTABLE_EMPTY = frozenset({"Point", "LineString"})


def to_rfc7946(geom, epsg, *, antimeridian: bool = True) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are read in shapely/GIS axis
        order, i.e. ``(x, y)`` = ``(easting, northing)`` or ``(longitude,
        latitude)``, regardless of the axis order the EPSG authority declares
        for ``epsg``.  A third ordinate is carried through as the GeoJSON
        altitude; an M ordinate is dropped (GeoJSON has no measure).
    epsg:
        Integer EPSG code of the CRS ``geom``'s coordinates are in.
    antimeridian:
        When true (default), geometries crossing the antimeridian are cut into
        parts that do not, as RFC 7946 §3.1.9 asks.  Lines and polygons may be
        promoted to their Multi- counterpart as a result.

    Returns
    -------
    dict
        A geometry object only -- ``{"type": ..., "coordinates": ...}``, or
        ``{"type": "GeometryCollection", "geometries": [...]}`` -- never a
        Feature and never a ``crs`` member.  It is JSON-serialisable as is.

    Conformance notes
    -----------------
    * Coordinates are reprojected to WGS 84 longitude/latitude, the only CRS
      RFC 7946 allows (§4).
    * Polygon rings follow the right-hand rule: exterior counterclockwise,
      interior clockwise (§3.1.6), and are explicitly closed.
    * Longitudes are wrapped into [-180, 180] and latitudes clamped to
      [-90, 90] (round-off only; a genuinely out-of-range latitude raises).
    * Nested GeometryCollections are flattened (§3.1.8), and empty members of
      collections and multi-geometries are dropped, since they carry nothing.

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry or ``epsg`` is not an integer.
    ValueError
        If ``epsg`` is unknown to PROJ, if a coordinate cannot be projected to
        WGS 84, or if the geometry has no valid RFC 7946 representation (an
        empty Point or LineString, or a degenerate ring).
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(
            "geom must be a shapely geometry, got %s" % type(geom).__name__
        )
    if isinstance(epsg, bool) or not isinstance(epsg, Integral):
        raise TypeError("epsg must be an integer EPSG code, got %r" % (epsg,))
    return _encode(geom, _transformer(int(epsg)), bool(antimeridian))


@lru_cache(maxsize=128)
def _transformer(epsg: int) -> Transformer:
    try:
        source = CRS.from_epsg(epsg)
    except CRSError as exc:
        raise ValueError("EPSG:%d is not a CRS known to PROJ" % epsg) from exc
    # always_xy keeps both ends in longitude/latitude (x/y) order, which is the
    # order shapely stores and the order RFC 7946 §3.1.1 mandates on output.
    return Transformer.from_crs(source, CRS.from_epsg(_WGS84), always_xy=True)


def _encode(geom, transformer: Transformer, antimeridian: bool) -> Dict[str, Any]:
    gtype = geom.geom_type
    if gtype == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_encode(part, transformer, antimeridian)
                           for part in _flatten(geom)],
        }
    if gtype == "LinearRing":  # a shapely type, not a GeoJSON one
        geom, gtype = LineString(geom.coords), "LineString"
    if gtype not in _SIMPLE_TYPES:
        raise ValueError("%s has no RFC 7946 representation" % gtype)
    if geom.is_empty:
        if gtype in _UNREPRESENTABLE_EMPTY:
            raise ValueError(
                "an empty %s has no valid RFC 7946 representation" % gtype
            )
        return {"type": gtype, "coordinates": []}

    lonlat = _to_wgs84(_drop_m(geom), transformer)
    if antimeridian and gtype not in ("Point", "MultiPoint"):
        lonlat, gtype = _cut_antimeridian(lonlat, gtype)
    return {"type": gtype, "coordinates": _coordinates(lonlat, gtype)}


def _flatten(collection):
    for part in collection.geoms:
        if part.is_empty:
            continue
        if part.geom_type == "GeometryCollection":
            yield from _flatten(part)
        else:
            yield part


def _drop_m(geom):
    """Remove any M ordinate, keeping Z when present."""
    if not getattr(shapely, "has_m", None) or not shapely.has_m(geom):
        return geom
    if not shapely.has_z(geom):
        return shapely.force_2d(geom)
    try:
        return shapely.transform(geom, lambda c: c, include_z=True, include_m=False)
    except TypeError:  # shapely without M-aware transform
        return shapely.force_2d(geom)


def _to_wgs84(geom, transformer: Transformer):
    include_z = bool(shapely.has_z(geom))

    def project(coords):
        out = np.column_stack(
            transformer.transform(*(coords[:, i] for i in range(coords.shape[1])))
        )
        if out.size:
            if not np.isfinite(out).all():
                raise ValueError(
                    "geometry has coordinates outside the domain of the source CRS"
                )
            lat = out[:, 1]
            if np.abs(lat).max() > _LAT_LIMIT + _LAT_TOL:
                raise ValueError("transformed latitude falls outside [-90, 90]")
            np.clip(lat, -_LAT_LIMIT, _LAT_LIMIT, out=lat)
        return out

    return shapely.transform(geom, project, include_z=include_z)


def _cut_antimeridian(geom, gtype: str):
    """Split a line or polygon so that no part crosses longitude +/-180."""
    multipart = gtype.startswith("Multi")
    base = gtype[5:] if multipart else gtype
    had_z = bool(shapely.has_z(geom))

    pieces: List[Any] = []
    for part in (shapely.get_parts(geom) if multipart else [geom]):
        if part.is_empty:
            continue
        part = _unwrap(part)
        minx, _, maxx, _ = part.bounds
        if minx >= -_LON_LIMIT and maxx <= _LON_LIMIT:
            pieces.append(part)
        else:
            pieces.extend(_split_into_periods(part))

    if not pieces:
        return geom, gtype
    if len(pieces) == 1 and not multipart:
        out = pieces[0]
    elif base == "Polygon":
        out, gtype = shapely.multipolygons(pieces), "MultiPolygon"
    else:
        out, gtype = shapely.multilinestrings(pieces), "MultiLineString"

    # Overlay may not carry Z through; keep one dimensionality throughout.
    if had_z and not _all_have_z(out):
        out = shapely.force_2d(out)
    return out, gtype


def _all_have_z(geom) -> bool:
    coords = shapely.get_coordinates(geom, include_z=True)
    return coords.size == 0 or not bool(np.isnan(coords[:, 2]).any())


def _unwrap(geom):
    """Make longitudes continuous, so a crossing reads as lon > 180 or < -180."""
    if geom.geom_type == "Polygon":
        shell = _unwrap_coords(geom.exterior.coords)
        centre = _mid_lon(shell)
        holes = []
        for ring in geom.interiors:
            hole = _unwrap_coords(ring.coords)
            shift = round((centre - _mid_lon(hole)) / _PERIOD)
            if shift:
                hole = [(c[0] + shift * _PERIOD,) + tuple(c[1:]) for c in hole]
            holes.append(hole)
        return Polygon(shell, holes)
    return LineString(_unwrap_coords(geom.coords))


def _unwrap_coords(coords):
    out = []
    previous = None
    for position in coords:
        lon = position[0]
        if previous is not None:
            while lon - previous > _LON_LIMIT:
                lon -= _PERIOD
            while lon - previous < -_LON_LIMIT:
                lon += _PERIOD
        out.append((lon,) + tuple(position[1:]))
        previous = lon
    return out


def _mid_lon(coords) -> float:
    lons = [c[0] for c in coords]
    return 0.5 * (min(lons) + max(lons))


def _split_into_periods(geom):
    """Clip an unwrapped geometry into 360-degree windows, each shifted home."""
    minx, _, maxx, _ = geom.bounds
    dimension = shapely.get_dimensions(geom)
    first = math.floor((minx + _LON_LIMIT) / _PERIOD)
    last = math.floor((maxx + _LON_LIMIT) / _PERIOD)

    pieces = []
    for k in range(first, last + 1):
        # Tall window: clip in longitude only, never in latitude.
        window = box(-_LON_LIMIT + k * _PERIOD, -100.0, _LON_LIMIT + k * _PERIOD, 100.0)
        try:
            clipped = geom.intersection(window)
        except GEOSException:
            return [geom]  # invalid input: leave it whole rather than fail
        for leaf in _leaves(clipped):
            # Drop the lower-dimensional slivers a boundary touch produces.
            if leaf.is_empty or shapely.get_dimensions(leaf) != dimension:
                continue
            pieces.append(translate(leaf, xoff=-k * _PERIOD) if k else leaf)
    return pieces or [geom]


def _leaves(geom):
    if geom.geom_type == "GeometryCollection" or geom.geom_type.startswith("Multi"):
        for part in geom.geoms:
            yield from _leaves(part)
    else:
        yield geom


def _coordinates(geom, gtype: str):
    if gtype == "Point":
        return _position(geom.coords[0])
    if gtype == "MultiPoint":
        return [_position(p.coords[0]) for p in geom.geoms if not p.is_empty]
    if gtype == "LineString":
        return _line(geom)
    if gtype == "MultiLineString":
        return [_line(line) for line in geom.geoms if not line.is_empty]
    if gtype == "Polygon":
        return _polygon(geom)
    return [_polygon(poly) for poly in geom.geoms if not poly.is_empty]


def _line(line) -> List[List[float]]:
    positions = [_position(c) for c in line.coords]
    if len(positions) < 2:
        raise ValueError("a LineString needs at least two positions")
    return positions


def _polygon(polygon) -> List[List[List[float]]]:
    rings = [_ring(polygon.exterior, counterclockwise=True)]
    rings.extend(_ring(ring, counterclockwise=False) for ring in polygon.interiors)
    return rings


def _ring(ring, counterclockwise: bool) -> List[List[float]]:
    positions = [_position(c) for c in ring.coords]
    if positions[0] != positions[-1]:
        positions.append(list(positions[0]))
    if len(positions) < 4:
        raise ValueError("a linear ring needs at least four positions")
    if _is_counterclockwise(positions) != counterclockwise:
        positions.reverse()
    return positions


def _is_counterclockwise(positions) -> bool:
    total = 0.0
    for i in range(len(positions) - 1):
        x1, y1 = positions[i][0], positions[i][1]
        x2, y2 = positions[i + 1][0], positions[i + 1][1]
        total += x1 * y2 - x2 * y1
    return total > 0.0


def _position(coordinate) -> List[float]:
    lon = _wrap_lon(float(coordinate[0]))
    lat = min(max(float(coordinate[1]), -_LAT_LIMIT), _LAT_LIMIT)
    if len(coordinate) > 2:
        return [lon, lat, float(coordinate[2])]
    return [lon, lat]


def _wrap_lon(lon: float) -> float:
    if -_LON_LIMIT <= lon <= _LON_LIMIT:
        return lon
    return math.remainder(lon, _PERIOD)