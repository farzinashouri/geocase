"""Strict RFC 7946 (GeoJSON) encoding of shapely geometries.

The single public entry point is :func:`to_rfc7946`.  Importing this module has
no side effects: CRS objects and coordinate transformers are built lazily on
first use and cached per thread (``pyproj.Transformer`` must not be shared
between threads).
"""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely.affinity import translate
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84_EPSG = 4326
_TOL = 1e-9          # degrees; well below the ~1e-7 that RFC 7946 §11.2 calls useful
_MAX_TILES = 1000    # sanity bound when cutting a geometry at the antimeridian

_MULTI_TYPES = {
    "MultiPoint": MultiPoint,
    "MultiLineString": MultiLineString,
    "MultiPolygon": MultiPolygon,
    "GeometryCollection": GeometryCollection,
}
_DIMENSION = {
    "Point": 0,
    "MultiPoint": 0,
    "LineString": 1,
    "LinearRing": 1,
    "MultiLineString": 1,
    "Polygon": 2,
    "MultiPolygon": 2,
}
_MULTI_OF_DIMENSION = {0: "MultiPoint", 1: "MultiLineString", 2: "MultiPolygon"}

_local = threading.local()


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def to_rfc7946(geom: BaseGeometry, epsg: int, *, precision: int | None = None) -> dict[str, Any]:
    """Return *geom* as a GeoJSON geometry object conforming to RFC 7946.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are read in easting/northing
        order (x first), which is how shapely geometries are conventionally
        stored no matter what axis order the EPSG registry declares for the
        CRS -- so ``x`` is longitude for geographic systems.
    epsg:
        Integer EPSG code of the CRS the coordinates are in, e.g. ``4326`` or
        ``3857``.
    precision:
        Optional number of decimal places to round to.  ``None`` (the default)
        keeps full precision; ``6`` is the ~10 cm compromise RFC 7946 §11.2
        suggests for keeping texts small.

    The result is a plain ``dict`` of plain ``float``/``str``/``list`` objects,
    ready for ``json.dumps``, with:

    * coordinates reprojected to WGS 84 decimal degrees in longitude, latitude
      (, altitude) order -- the only CRS RFC 7946 §4 allows;
    * polygon rings closed, at least four positions long, and wound by the
      right-hand rule -- exteriors counterclockwise, holes clockwise (§3.1.6);
    * geometries crossing the antimeridian cut in two, so no part's
      representation crosses it (§3.1.9);
    * nested GeometryCollections flattened (§3.1.8) and empty members dropped;
    * any M ordinate dropped (GeoJSON positions carry at most three elements,
      §3.1.1) while Z is kept as the altitude element.

    Raises ``TypeError`` for a non-geometry input and ``ValueError`` for an
    unknown EPSG code, coordinates with no finite WGS 84 equivalent, or empty
    Points/LineStrings, which RFC 7946 cannot express (an empty Polygon or
    Multi* geometry is written with an empty ``coordinates`` array).

    Limitations: only existing vertices are transformed, so densify long
    segments first if you need the reprojected shape to follow the projection's
    curvature.  Following the usual GeoJSON convention, a segment spanning more
    than 180 degrees of longitude is read as an antimeridian crossing unless
    both of its endpoints lie on the antimeridian.  Polygons enclosing a pole
    are not special-cased.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    try:
        code = int(epsg)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"epsg must be an integer EPSG code, got {epsg!r}") from exc
    if precision is not None and (isinstance(precision, bool) or not isinstance(precision, int) or precision < 0):
        raise ValueError(f"precision must be a non-negative integer or None, got {precision!r}")

    lonlat = _rebuild(geom, lambda coords: _reproject(coords, _transformer(code), code))
    return _geometry_dict(_split_antimeridian(lonlat), precision)


# --------------------------------------------------------------------------- #
# reprojection
# --------------------------------------------------------------------------- #
def _transformer(epsg: int) -> Transformer | None:
    """Cached per-thread transformer to WGS 84, or None when already WGS 84."""
    cache = getattr(_local, "transformers", None)
    if cache is None:
        cache = _local.transformers = {}
    if epsg not in cache:
        try:
            source = CRS.from_epsg(epsg)
        except CRSError as exc:
            raise ValueError(f"not a usable EPSG code: {epsg!r}") from exc
        target = CRS.from_epsg(_WGS84_EPSG)
        cache[epsg] = None if source.equals(target) else Transformer.from_crs(source, target, always_xy=True)
    return cache[epsg]


def _coord_list(geom: BaseGeometry) -> list[tuple[float, ...]]:
    """Coordinates of a single-part geometry, keeping x, y (and z), dropping m."""
    width = 3 if geom.has_z else 2
    return [tuple(c[:width]) for c in geom.coords]


def _reproject(coords, transformer, code):
    if not coords:
        return []
    if transformer is None:
        out = [tuple(float(v) for v in c) for c in coords]
    else:
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        if len(coords[0]) > 2:
            zs = [c[2] for c in coords]
            transformed = transformer.transform(xs, ys, zs)
        else:
            transformed = transformer.transform(xs, ys)
        out = [tuple(float(v) for v in position) for position in zip(*transformed)]
    for source, target in zip(coords, out):
        if not all(map(math.isfinite, target)):
            raise ValueError(f"coordinate {tuple(source)} in EPSG:{code} has no finite WGS 84 equivalent")
    return out


def _assemble(kind: str, parts: list[BaseGeometry]) -> BaseGeometry:
    # Empty parts have no GeoJSON representation of their own, so drop them.
    return _MULTI_TYPES[kind]([part for part in parts if not part.is_empty])


def _rebuild(geom: BaseGeometry, fn) -> BaseGeometry:
    """Copy *geom* with every coordinate sequence replaced by ``fn(sequence)``."""
    kind = geom.geom_type
    if geom.is_empty:
        return geom
    if kind == "Point":
        return Point(fn(_coord_list(geom))[0])
    if kind == "LinearRing":
        return LinearRing(fn(_coord_list(geom)))
    if kind == "LineString":
        return LineString(fn(_coord_list(geom)))
    if kind == "Polygon":
        return Polygon(
            fn(_coord_list(geom.exterior)),
            [fn(_coord_list(ring)) for ring in geom.interiors],
        )
    if kind in _MULTI_TYPES:
        return _assemble(kind, [_rebuild(part, fn) for part in geom.geoms])
    raise TypeError(f"unsupported geometry type: {kind}")


# --------------------------------------------------------------------------- #
# antimeridian cutting (RFC 7946 §3.1.9)
# --------------------------------------------------------------------------- #
def _wrap_lon(lon: float) -> float:
    """Fold a longitude into [-180, 180], keeping an exact +/-180 intact."""
    return math.remainder(float(lon), 360.0)


def _on_antimeridian(lon: float) -> bool:
    return abs(abs(lon) - 180.0) <= _TOL


def _unwrap(coords):
    """Make longitudes continuous, reading a jump wider than 180 deg as a crossing.

    A segment whose two endpoints both sit on the antimeridian is left alone:
    that is the world-wide box ``-180 .. 180``, which spans the globe the long
    way round rather than crossing anything.
    """
    out: list[tuple[float, ...]] = []
    offset = 0.0
    previous = None
    for coord in coords:
        lon = _wrap_lon(coord[0])
        if previous is not None:
            delta = lon + offset - out[-1][0]
            if abs(delta) > 180.0 + _TOL and not (_on_antimeridian(lon) and _on_antimeridian(previous)):
                offset -= 360.0 * math.floor((delta + 180.0) / 360.0)
        out.append((lon + offset,) + tuple(coord[1:]))
        previous = lon
    return out


def _unwrap_geom(geom: BaseGeometry) -> BaseGeometry:
    if geom.geom_type == "Polygon":
        shell = _unwrap(_coord_list(geom.exterior))
        centre = (min(p[0] for p in shell) + max(p[0] for p in shell)) / 2.0
        holes = []
        for ring in geom.interiors:
            hole = _unwrap(_coord_list(ring))
            hole_centre = (min(p[0] for p in hole) + max(p[0] for p in hole)) / 2.0
            shift = 360.0 * round((centre - hole_centre) / 360.0)
            if shift:
                hole = [(p[0] + shift,) + tuple(p[1:]) for p in hole]
            holes.append(hole)
        return Polygon(shell, holes)
    return type(geom)(_unwrap(_coord_list(geom)))


def _explode(geom: BaseGeometry) -> list[BaseGeometry]:
    if geom.geom_type == "GeometryCollection":
        return [leaf for part in geom.geoms for leaf in _explode(part)]
    if geom.geom_type in _MULTI_TYPES:
        return list(geom.geoms)
    return [geom]


def _all_finite(geom: BaseGeometry) -> bool:
    coords = shapely.get_coordinates(geom, include_z=geom.has_z)
    return bool(coords.size == 0 or np.isfinite(coords).all())


def _cut(geom: BaseGeometry, low: int, high: int) -> BaseGeometry:
    """Clip *geom* to each 360 deg wide tile it spans and fold the pieces back."""
    dimension = _DIMENSION[geom.geom_type]
    pieces: list[BaseGeometry] = []
    for k in range(low, high + 1):
        # The latitude range is deliberately far wider than the globe: only
        # longitude is being clipped here.
        tile = box(k * 360.0 - 180.0, -1.0e5, k * 360.0 + 180.0, 1.0e5)
        clipped = geom.intersection(tile)
        if clipped.is_empty:
            continue
        clipped = translate(clipped, xoff=-360.0 * k)
        for part in _explode(clipped):
            # Touching a tile edge yields lower-dimensional crumbs; drop those.
            if not part.is_empty and _DIMENSION.get(part.geom_type) == dimension:
                pieces.append(part)
    if not pieces:
        return geom
    if len(pieces) == 1:
        return pieces[0]
    return _assemble(_MULTI_OF_DIMENSION[dimension], pieces)


def _split_part(geom: BaseGeometry) -> BaseGeometry:
    if geom.is_empty:
        return geom
    if geom.geom_type == "Point":
        coord = _coord_list(geom)[0]
        return Point((_wrap_lon(coord[0]),) + tuple(coord[1:]))

    unwrapped = _unwrap_geom(geom)
    minx, _, maxx, _ = unwrapped.bounds
    low = math.floor((minx + 180.0) / 360.0)
    high = math.floor((maxx + 180.0) / 360.0)
    # Sitting exactly on a tile edge is not reaching into the next tile.
    if high > low and (maxx + 180.0) % 360.0 <= _TOL:
        high -= 1
    if high > low and (minx + 180.0) % 360.0 >= 360.0 - _TOL:
        low += 1
    if low == high:
        return translate(unwrapped, xoff=-360.0 * low) if low else unwrapped
    if high - low + 1 > _MAX_TILES:
        raise ValueError("geometry wraps the globe too many times to cut at the antimeridian")

    pieces = _cut(unwrapped, low, high)
    if unwrapped.has_z and not _all_finite(pieces):
        # GEOS could not carry elevations across the cut; a conforming 2D
        # geometry beats one with unrepresentable NaN altitudes.
        pieces = _cut(shapely.force_2d(unwrapped), low, high)
    return pieces


def _split_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    kind = geom.geom_type
    if geom.is_empty:
        return geom
    if kind == "GeometryCollection":
        return GeometryCollection([_split_antimeridian(part) for part in geom.geoms])
    if kind in _MULTI_TYPES:
        parts: list[BaseGeometry] = []
        for part in geom.geoms:
            parts.extend(_explode(_split_part(part)))
        return _assemble(kind, parts)
    return _split_part(geom)


# --------------------------------------------------------------------------- #
# GeoJSON encoding
# --------------------------------------------------------------------------- #
def _number(value: float, precision: int | None) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("coordinates must be finite numbers")
    if precision is not None:
        number = round(number, precision)
    return 0.0 if number == 0.0 else number  # never emit -0.0


def _clamp_latitude(value: float) -> float:
    latitude = float(value)
    if 90.0 < latitude <= 90.0 + _TOL:  # projection round-off, not real data
        return 90.0
    if -90.0 - _TOL <= latitude < -90.0:
        return -90.0
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude {latitude} is outside [-90, 90]")
    return latitude


def _position(coord, precision: int | None) -> list[float]:
    longitude = _number(coord[0], precision)
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude {longitude} is outside [-180, 180]")
    position = [longitude, _number(_clamp_latitude(coord[1]), precision)]
    if len(coord) > 2:
        position.append(_number(coord[2], precision))
    return position


def _signed_area(ring: list[list[float]]) -> float:
    total = 0.0
    for start, end in zip(ring, ring[1:]):
        total += start[0] * end[1] - end[0] * start[1]
    return total / 2.0


def _linear_ring(ring: LinearRing, precision: int | None, *, ccw: bool) -> list[list[float]]:
    coordinates = [_position(coord, precision) for coord in _coord_list(ring)]
    if coordinates[0] != coordinates[-1]:
        coordinates.append(list(coordinates[0]))
    if len(coordinates) < 4:
        raise ValueError("a GeoJSON linear ring needs at least four positions")
    area = _signed_area(coordinates)
    if (ccw and area < 0.0) or (not ccw and area > 0.0):
        coordinates.reverse()
    return coordinates


def _collection(geom: GeometryCollection, precision: int | None) -> list[dict[str, Any]]:
    geometries: list[dict[str, Any]] = []
    for part in geom.geoms:
        if part.is_empty:
            continue
        if part.geom_type == "GeometryCollection":
            geometries.extend(_collection(part, precision))  # §3.1.8: avoid nesting
        else:
            geometries.append(_geometry_dict(part, precision))
    return geometries


def _geometry_dict(geom: BaseGeometry, precision: int | None) -> dict[str, Any]:
    kind = geom.geom_type
    if kind == "Point":
        if geom.is_empty:
            raise ValueError("an empty Point has no RFC 7946 representation")
        return {"type": "Point", "coordinates": _position(_coord_list(geom)[0], precision)}
    if kind in ("LineString", "LinearRing"):
        if geom.is_empty:
            raise ValueError("an empty LineString has no RFC 7946 representation")
        coordinates = [_position(coord, precision) for coord in _coord_list(geom)]
        if len(coordinates) < 2:
            raise ValueError("a GeoJSON LineString needs at least two positions")
        return {"type": "LineString", "coordinates": coordinates}
    if kind == "Polygon":
        if geom.is_empty:
            return {"type": "Polygon", "coordinates": []}
        rings = [_linear_ring(geom.exterior, precision, ccw=True)]
        rings.extend(_linear_ring(ring, precision, ccw=False) for ring in geom.interiors)
        return {"type": "Polygon", "coordinates": rings}
    if kind == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [
                _position(_coord_list(part)[0], precision) for part in geom.geoms if not part.is_empty
            ],
        }
    if kind in ("MultiLineString", "MultiPolygon"):
        return {
            "type": kind,
            "coordinates": [
                _geometry_dict(part, precision)["coordinates"] for part in geom.geoms if not part.is_empty
            ],
        }
    if kind == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": _collection(geom, precision)}
    raise TypeError(f"unsupported geometry type: {kind}")