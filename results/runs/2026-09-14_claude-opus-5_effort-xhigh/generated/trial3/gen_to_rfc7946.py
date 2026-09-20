"""Strict RFC 7946 (GeoJSON) encoding for shapely geometries.

The module exposes a single function, :func:`to_rfc7946`, which turns a shapely
geometry plus the EPSG code its coordinates live in into a plain ``dict``
holding a GeoJSON *geometry object*.

What "strictly conforming" means here, and the choices it forces:

* **CRS** (RFC 7946 §4) -- GeoJSON coordinates are always WGS 84 longitude /
  latitude in decimal degrees, so the geometry is reprojected from ``epsg``.
  The input is read in traditional GIS axis order, i.e. ``x`` is easting /
  longitude and ``y`` is northing / latitude, regardless of the axis order the
  EPSG registry declares for the source CRS (``always_xy=True``).  No ``crs``
  member is emitted; RFC 7946 removed it.
* **Positions** (§3.1.1) -- ``[lon, lat]`` or ``[lon, lat, elevation]``.  A
  measure (M) ordinate has no place in GeoJSON and is dropped; Z is kept.
* **Antimeridian** (§3.1.9) -- geometries that cross the antimeridian are cut
  in two, so a ``LineString`` may come back as a ``MultiLineString`` and a
  ``Polygon`` as a ``MultiPolygon``.  Consecutive positions more than 180
  degrees apart in longitude are read as crossing the antimeridian, which is
  the reading the RFC's own examples use.  Cutting a polygon runs through a
  planar overlay, so Z is dropped from polygonal output that had to be cut.
* **Ring winding** (§3.1.6) -- exterior rings are made counterclockwise and
  holes clockwise, and every ring is explicitly closed.
* ``LinearRing`` has no GeoJSON counterpart and is encoded as a ``LineString``;
  a ``GeometryCollection`` is encoded with a ``geometries`` member (§3.1.8).
* Empty geometries produce an empty ``coordinates`` array, which §3.1 permits.

Importing this module performs no I/O; the PROJ database is only touched on the
first call.
"""

from __future__ import annotations

import math
from functools import lru_cache
from numbers import Integral
from typing import Any, Dict, List, Optional, Sequence

from pyproj import CRS, Transformer
from shapely.geometry import Polygon, box

__all__ = ["to_rfc7946"]

# Nesting depth of the "coordinates" member, per GeoJSON geometry type.
_DEPTH = {
    "Point": 0,
    "MultiPoint": 1,
    "LineString": 1,
    "MultiLineString": 2,
    "Polygon": 2,
    "MultiPolygon": 3,
}

_TOL = 1e-9  # tolerance for snapping coordinates back into their valid range


def to_rfc7946(geom: Any, epsg: int) -> Dict[str, Any]:
    """Encode a shapely geometry as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are interpreted as ``(x, y)`` =
        ``(easting, northing)`` / ``(longitude, latitude)``.
    epsg:
        Integer EPSG code of the CRS ``geom`` is expressed in, e.g. ``4326`` or
        ``3857``.

    Returns
    -------
    dict
        A GeoJSON geometry object with ``type`` and ``coordinates`` members
        (``geometries`` instead of ``coordinates`` for a geometry collection),
        built from plain ``dict``/``list``/``float`` values and therefore
        directly serialisable with :mod:`json`.

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry or ``epsg`` is not an integer.
    ValueError
        If ``epsg`` is not a known EPSG code, if a coordinate cannot be
        reprojected onto the ellipsoid, or if the geometry winds around a pole,
        which RFC 7946 cannot represent unambiguously.
    """
    if isinstance(epsg, bool) or not isinstance(epsg, Integral):
        raise TypeError("epsg must be an integer EPSG code")
    return _convert(geom, _transformer(int(epsg)))


@lru_cache(maxsize=None)
def _transformer(epsg: int) -> Optional[Transformer]:
    """Transformer from ``epsg`` to WGS 84 lon/lat, or None if none is needed."""
    try:
        source = CRS.from_epsg(epsg)
    except Exception as exc:  # pyproj raises CRSError for unknown codes
        raise ValueError(f"unknown EPSG code: {epsg}") from exc
    target = CRS.from_epsg(4326)
    if source == target:
        return None
    return Transformer.from_crs(source, target, always_xy=True)


def _convert(geom: Any, transformer: Optional[Transformer]) -> Dict[str, Any]:
    geom_type = getattr(geom, "geom_type", None)
    if geom_type is None:
        raise TypeError("geom must be a shapely geometry")

    if geom_type == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_convert(part, transformer) for part in geom.geoms],
        }

    # A shapely LinearRing is just a closed LineString as far as GeoJSON cares.
    gtype = "LineString" if geom_type == "LinearRing" else geom_type
    if gtype not in _DEPTH:
        raise TypeError(f"unsupported geometry type: {geom_type}")
    if geom.is_empty:
        return {"type": gtype, "coordinates": []}

    has_z = bool(geom.has_z)
    coords = _coordinates(geom, geom_type, 3 if has_z else 2)

    positions: List[List[float]] = []
    _collect(coords, _DEPTH[gtype], positions)
    _reproject(positions, transformer, has_z)
    _check(positions)

    # Cutting a polygon is a planar overlay and cannot carry Z through, so drop
    # it up front to keep the whole geometry uniformly two-dimensional.
    if has_z and gtype in ("Polygon", "MultiPolygon"):
        rings = [coords] if gtype == "Polygon" else coords
        if any(_crosses(polygon[0]) for polygon in rings):
            for position in positions:
                del position[2:]

    gtype, coords = _cut_antimeridian(gtype, coords)
    return {"type": gtype, "coordinates": _encode(gtype, coords)}


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

def _coordinates(geom: Any, geom_type: str, n: int) -> Any:
    """Nested lists of positions, truncated to ``n`` ordinates (drops M)."""
    if geom_type == "Point":
        return _position_of(geom, n)
    if geom_type in ("LineString", "LinearRing"):
        return _line(geom, n)
    if geom_type == "Polygon":
        return _rings(geom, n)
    if geom_type == "MultiPoint":
        return [_position_of(p, n) for p in geom.geoms if not p.is_empty]
    if geom_type == "MultiLineString":
        return [_line(ls, n) for ls in geom.geoms if not ls.is_empty]
    if geom_type == "MultiPolygon":
        return [_rings(p, n) for p in geom.geoms if not p.is_empty]
    raise TypeError(f"unsupported geometry type: {geom_type}")


def _position_of(point: Any, n: int) -> List[float]:
    return [float(v) for v in point.coords[0][:n]]


def _line(geom: Any, n: int) -> List[List[float]]:
    return [[float(v) for v in position[:n]] for position in geom.coords]


def _rings(polygon: Any, n: int) -> List[List[List[float]]]:
    return [_line(ring, n) for ring in (polygon.exterior, *polygon.interiors)]


def _collect(coords: Any, depth: int, out: List[List[float]]) -> None:
    if depth == 0:
        out.append(coords)
        return
    for child in coords:
        _collect(child, depth - 1, out)


# --------------------------------------------------------------------------- #
# Reprojection
# --------------------------------------------------------------------------- #

def _reproject(
    positions: Sequence[List[float]],
    transformer: Optional[Transformer],
    has_z: bool,
) -> None:
    """Reproject ``positions`` to WGS 84 lon/lat in place."""
    if transformer is None or not positions:
        return
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    if has_z:
        zs = [p[2] for p in positions]
        xs, ys, zs = transformer.transform(xs, ys, zs)
        for position, x, y, z in zip(positions, xs, ys, zs):
            position[0], position[1], position[2] = float(x), float(y), float(z)
    else:
        xs, ys = transformer.transform(xs, ys)
        for position, x, y in zip(positions, xs, ys):
            position[0], position[1] = float(x), float(y)


def _check(positions: Sequence[List[float]]) -> None:
    """Reject coordinates that cannot be written as valid JSON or valid WGS 84."""
    for position in positions:
        if not all(math.isfinite(v) for v in position):
            raise ValueError(
                f"coordinate {tuple(position)} could not be reprojected to WGS 84"
            )
        if abs(position[1]) > 90.0 + _TOL:
            raise ValueError(f"latitude out of range after reprojection: {position[1]}")


# --------------------------------------------------------------------------- #
# Antimeridian handling (RFC 7946 section 3.1.9)
# --------------------------------------------------------------------------- #

def _strip(lon: float) -> int:
    """Index of the 360-degree-wide band containing ``lon``; band 0 is [-180, 180]."""
    return math.floor((lon + 180.0) / 360.0)


def _boundaries(lo: float, hi: float) -> List[float]:
    """Antimeridian copies (180 + 360k) lying strictly inside ``(lo, hi)``."""
    if hi <= lo:
        return []
    first = math.floor((lo - 180.0) / 360.0) + 1
    last = math.ceil((hi - 180.0) / 360.0) - 1
    return [180.0 + 360.0 * k for k in range(first, last + 1)]


def _shift(position: Sequence[float], dx: float) -> List[float]:
    return [position[0] + dx, *position[1:]]


def _unwrap(points: Sequence[Sequence[float]]) -> List[List[float]]:
    """Make longitudes continuous by undoing wrap-around at the antimeridian."""
    out = [list(points[0])]
    offset = 0.0
    previous = points[0][0]
    for point in points[1:]:
        lon = point[0]
        delta = lon - previous
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        out.append(_shift(point, offset))
        previous = lon
    return out


def _crosses(points: Sequence[Sequence[float]]) -> bool:
    unwrapped = _unwrap(points)
    lons = [p[0] for p in unwrapped]
    return bool(_boundaries(min(lons), max(lons)))


def _interpolate(a: Sequence[float], b: Sequence[float], lon: float) -> List[float]:
    t = (lon - a[0]) / (b[0] - a[0])
    point = [lon, a[1] + t * (b[1] - a[1])]
    if len(a) > 2 and len(b) > 2:
        point.append(a[2] + t * (b[2] - a[2]))
    return point


def _split_line(points: Sequence[Sequence[float]]) -> List[List[List[float]]]:
    """Cut a line at every antimeridian crossing and wrap each piece into range."""
    if len(points) < 2:
        return [[list(p) for p in points]] if points else []

    # Densify so that no segment spans more than one band ...
    unwrapped = _unwrap(points)
    dense = [unwrapped[0]]
    for a, b in zip(unwrapped, unwrapped[1:]):
        crossings = _boundaries(min(a[0], b[0]), max(a[0], b[0]))
        if b[0] < a[0]:
            crossings.reverse()
        dense.extend(_interpolate(a, b, lon) for lon in crossings)
        dense.append(b)

    # ... then break the line wherever consecutive segments change band.
    pieces: List[List[Any]] = []
    current = [dense[0]]
    band: Optional[int] = None
    for a, b in zip(dense, dense[1:]):
        segment_band = _strip((a[0] + b[0]) / 2.0)
        if band is not None and segment_band != band:
            pieces.append([band, current])
            current = [list(a)]
        current.append(b)
        band = segment_band
    pieces.append([band or 0, current])

    return [
        [_shift(p, -360.0 * k) for p in piece]
        for k, piece in pieces
        if len(piece) >= 2
    ]


def _align(ring: List[List[float]], centre: float) -> List[List[float]]:
    """Move a hole by a whole turn so it shares the exterior ring's frame."""
    lons = [p[0] for p in ring]
    k = round(((min(lons) + max(lons)) / 2.0 - centre) / 360.0)
    return ring if k == 0 else [_shift(p, -360.0 * k) for p in ring]


def _split_polygon(rings: Sequence[Sequence[Sequence[float]]]) -> List[List[List[List[float]]]]:
    """Cut a polygon at the antimeridian, returning one entry per output polygon."""
    exterior = _unwrap(rings[0])
    if abs(exterior[-1][0] - exterior[0][0]) > 180.0:
        raise ValueError(
            "geometry winds around a pole and has no unambiguous RFC 7946 "
            "representation; split it at the pole before converting"
        )

    lons = [p[0] for p in exterior]
    lo, hi = min(lons), max(lons)
    holes = [_align(_unwrap(ring), (lo + hi) / 2.0) for ring in rings[1:]]

    if not _boundaries(lo, hi):  # fits in one band: shift, never cut
        dx = -360.0 * _strip((lo + hi) / 2.0)
        if dx == 0.0:
            return [[exterior, *holes]]
        return [[[_shift(p, dx) for p in ring] for ring in (exterior, *holes)]]

    shell = [(p[0], p[1]) for p in exterior]
    polygon = Polygon(shell, [[(p[0], p[1]) for p in hole] for hole in holes])
    parts: List[List[List[List[float]]]] = []
    for k in range(_strip(lo), _strip(hi) + 1):
        band = box(-180.0 + 360.0 * k, -1e6, 180.0 + 360.0 * k, 1e6)
        try:
            clipped = polygon.intersection(band)
        except Exception as exc:  # GEOS refuses to overlay invalid input
            raise ValueError(
                "polygon is invalid and cannot be cut at the antimeridian"
            ) from exc
        for part in _polygons(clipped):
            parts.append(
                [
                    [[x - 360.0 * k, y] for x, y in ring.coords]
                    for ring in (part.exterior, *part.interiors)
                ]
            )
    return parts


def _polygons(geom: Any) -> List[Any]:
    """Every Polygon inside an overlay result, which may be a mixed collection."""
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [p for part in geom.geoms for p in _polygons(part)]
    return []


def _cut_antimeridian(gtype: str, coords: Any) -> Any:
    if gtype == "Point":
        return gtype, coords
    if gtype == "MultiPoint":
        return gtype, coords
    if gtype == "LineString":
        pieces = _split_line(coords)
        return ("LineString", pieces[0]) if len(pieces) == 1 else ("MultiLineString", pieces)
    if gtype == "MultiLineString":
        return gtype, [piece for line in coords for piece in _split_line(line)]
    if gtype == "Polygon":
        parts = _split_polygon(coords)
        return ("Polygon", parts[0]) if len(parts) == 1 else ("MultiPolygon", parts)
    return gtype, [part for rings in coords for part in _split_polygon(rings)]


# --------------------------------------------------------------------------- #
# Encoding
# --------------------------------------------------------------------------- #

def _wrap_lon(lon: float) -> float:
    if -180.0 <= lon <= 180.0:
        return lon
    if abs(abs(lon) - 180.0) < _TOL:  # float noise, not a real crossing
        return math.copysign(180.0, lon)
    return math.remainder(lon, 360.0)


def _position(position: Sequence[float]) -> List[float]:
    out = [_wrap_lon(float(position[0])), min(90.0, max(-90.0, float(position[1])))]
    if len(position) > 2:
        out.append(float(position[2]))
    return out


def _signed_area(ring: Sequence[Sequence[float]]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:])) / 2.0


def _encode_rings(rings: Sequence[Sequence[Sequence[float]]]) -> List[List[List[float]]]:
    """Close every ring and apply the right-hand rule: shell CCW, holes CW."""
    out = []
    for index, ring in enumerate(rings):
        points = [_position(p) for p in ring]
        if points[0] != points[-1]:
            points.append(list(points[0]))
        if len(points) >= 4:
            area = _signed_area(points)
            if (area < 0.0) if index == 0 else (area > 0.0):
                points.reverse()
        out.append(points)
    return out


def _encode(gtype: str, coords: Any) -> Any:
    if gtype == "Point":
        return _position(coords)
    if gtype in ("MultiPoint", "LineString"):
        return [_position(p) for p in coords]
    if gtype == "MultiLineString":
        return [[_position(p) for p in line] for line in coords]
    if gtype == "Polygon":
        return _encode_rings(coords)
    return [_encode_rings(rings) for rings in coords]