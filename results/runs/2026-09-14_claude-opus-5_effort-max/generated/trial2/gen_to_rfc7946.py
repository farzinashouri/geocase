"""Strict RFC 7946 (GeoJSON) encoding of shapely geometries.

``to_rfc7946(geom, epsg)`` returns the geometry as a plain ``dict``: a GeoJSON
geometry object carrying only the members RFC 7946 defines for it (``type``
plus ``coordinates``, or ``geometries`` for a GeometryCollection), ready to
hand to ``json.dumps``.

Conformance notes, by section of the RFC:

* Section 4 -- GeoJSON coordinates are always WGS 84 longitude/latitude in
  decimal degrees (OGC:CRS84), so coordinates are reprojected from ``epsg``
  with ``always_xy=True``; the axis order the EPSG registry records for the
  source is irrelevant because shapely stores x/easting first.  An optional
  third element SHALL be a height in metres above the WGS 84 ellipsoid, so
  geometries carrying z are transformed to EPSG:4979 rather than EPSG:4326 --
  that lets PROJ apply a vertical transformation when the source CRS has one.
  No ``crs`` member is emitted; RFC 7946 removed it.
* Section 3.1.1 -- a position is two or three numbers.  Shapely M ordinates
  are dropped rather than emitted as a fourth element.
* Section 3.1.6 -- linear rings follow the right-hand rule: exterior rings
  counterclockwise, holes clockwise.  Winding is evaluated *after*
  reprojection, because a change of projection can reverse it, and each ring
  is closed exactly (last position set equal to the first).
* Section 3.1.8 -- nested GeometryCollections are flattened to one level.
* RFC 8259 -- every coordinate is a finite Python ``float``.  A non-finite
  result (a point outside the source projection's domain, a NaN ordinate)
  raises ``ValueError`` rather than producing JSON no strict parser accepts.
* Empty geometries -- ``Polygon``, the three multi-part types and
  ``GeometryCollection`` have valid empty encodings and get them; an empty
  ``Point`` or ``LineString`` has none (the RFC requires one position and two
  positions respectively), so those raise ``ValueError``.
* A shapely ``LinearRing`` is encoded as ``LineString``: RFC 7946 has no
  standalone ring type.

Deliberately not done: section 3.1.9 antimeridian cutting.  It is a SHOULD,
and splitting geometries at +/-180 degrees correctly -- polygons enclosing a
pole, rings that wrap the globe -- means rewriting the caller's topology on a
guess.  Longitudes are wrapped into [-180, 180], but a shape spanning the
antimeridian is left whole and naive renderers will draw it the long way
round.

Importing this module has no side effects; CRS and transformer objects are
built lazily on first use and cached.
"""

from __future__ import annotations

import math
import numbers
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError, ProjError
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

Position = List[float]
Ring = List[Position]

# WGS 84 lon/lat, and lon/lat/ellipsoidal height: already the GeoJSON CRS.
_WGS84_2D = 4326
_WGS84_3D = 4979
_ALREADY_WGS84 = frozenset({_WGS84_2D, _WGS84_3D})

# A pole may be overshot by a rounding error; more than this is a real error.
_LAT_TOLERANCE = 1e-9


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Convert a shapely geometry to an RFC 7946 geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are interpreted with x first
        (easting or longitude), which is shapely's own convention.
    epsg:
        EPSG code of the CRS ``geom``'s coordinates are in, e.g. ``4326`` or
        ``3857``.

    Returns
    -------
    dict
        A GeoJSON geometry object in WGS 84 longitude/latitude, containing
        only ``type`` and ``coordinates`` (or ``geometries``).

    Raises
    ------
    TypeError
        ``geom`` is not a shapely geometry, ``epsg`` is not an integer, or the
        geometry type has no GeoJSON equivalent.
    ValueError
        ``epsg`` is not a known EPSG code, the geometry is an empty Point or
        LineString, or a coordinate is not finite after reprojection.
    pyproj.exceptions.ProjError
        The reprojection itself failed.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(
            "geom must be a shapely geometry, got " + type(geom).__name__
        )
    if isinstance(epsg, bool) or not isinstance(epsg, numbers.Integral):
        raise TypeError("epsg must be an integer EPSG code, got %r" % (epsg,))

    positions: List[Position] = []
    rings: List[Tuple[Ring, bool]] = []

    # Build the output first, holding on to every position list and every ring
    # so both can be fixed up in place afterwards.
    obj = _encode(geom, positions, rings)
    _reproject(positions, int(epsg))
    _orient(rings)
    return obj


# --------------------------------------------------------------------------
# structure
# --------------------------------------------------------------------------


def _encode(
    geom: BaseGeometry,
    positions: List[Position],
    rings: List[Tuple[Ring, bool]],
) -> Dict[str, Any]:
    kind = geom.geom_type

    if kind == "Point":
        return {"type": "Point", "coordinates": _point(geom, positions)}
    if kind in ("LineString", "LinearRing"):
        return {"type": "LineString", "coordinates": _line(geom, positions)}
    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon(geom, positions, rings)}
    if kind == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [_point(part, positions) for part in geom.geoms],
        }
    if kind == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [_line(part, positions) for part in geom.geoms],
        }
    if kind == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                _polygon(part, positions, rings) for part in geom.geoms
            ],
        }
    if kind == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [
                _encode(member, positions, rings) for member in _flatten(geom)
            ],
        }
    raise TypeError("geometry type %r has no RFC 7946 equivalent" % (kind,))


def _flatten(collection: BaseGeometry) -> Iterator[BaseGeometry]:
    """Yield members, dissolving nested GeometryCollections (section 3.1.8)."""
    for member in collection.geoms:
        if member.geom_type == "GeometryCollection":
            for nested in _flatten(member):
                yield nested
        else:
            yield member


def _point(geom: BaseGeometry, positions: List[Position]) -> Position:
    if geom.is_empty:
        raise ValueError(
            "an empty Point has no RFC 7946 representation: the coordinates "
            "member of a Point must be a position"
        )
    return _coords(geom, positions)[0]


def _line(geom: BaseGeometry, positions: List[Position]) -> List[Position]:
    if geom.is_empty:
        raise ValueError(
            "an empty LineString has no RFC 7946 representation: the "
            "coordinates member of a LineString needs two or more positions"
        )
    return _coords(geom, positions)


def _polygon(
    geom: BaseGeometry,
    positions: List[Position],
    rings: List[Tuple[Ring, bool]],
) -> List[Ring]:
    if geom.is_empty:
        return []
    out = [_ring(geom.exterior, True, positions, rings)]
    for interior in geom.interiors:
        out.append(_ring(interior, False, positions, rings))
    return out


def _ring(
    ring: BaseGeometry,
    counterclockwise: bool,
    positions: List[Position],
    rings: List[Tuple[Ring, bool]],
) -> Ring:
    coords = _coords(ring, positions)
    if len(coords) < 4:
        raise ValueError(
            "a linear ring needs four or more positions, got %d" % len(coords)
        )
    rings.append((coords, counterclockwise))
    return coords


def _coords(geom: BaseGeometry, positions: List[Position]) -> List[Position]:
    """Positions of a simple geometry, registered for later reprojection.

    The slice keeps two or three ordinates: shapely may expose an M value as a
    further element, and RFC 7946 section 3.1.1 says positions should not be
    extended past three.
    """
    width = 3 if geom.has_z else 2
    out = []
    for coord in geom.coords:
        position = [float(value) for value in coord[:width]]
        positions.append(position)
        out.append(position)
    return out


# --------------------------------------------------------------------------
# coordinates
# --------------------------------------------------------------------------


@lru_cache(maxsize=32)
def _transformer(epsg: int, vertical: bool) -> Optional[Transformer]:
    """Transformer from ``epsg`` to WGS 84, or None if already there."""
    if epsg in _ALREADY_WGS84:
        return None
    try:
        source = CRS.from_epsg(epsg)
    except CRSError as exc:
        raise ValueError("unknown EPSG code: %d" % epsg) from exc
    if vertical:
        try:
            return Transformer.from_crs(
                source, CRS.from_epsg(_WGS84_3D), always_xy=True
            )
        except (CRSError, ProjError):
            # No 3D operation available; fall back to the 2D target, which
            # leaves heights untouched -- the best that can be done here.
            pass
    return Transformer.from_crs(source, CRS.from_epsg(_WGS84_2D), always_xy=True)


def _reproject(positions: Sequence[Position], epsg: int) -> None:
    """Rewrite every registered position in place as WGS 84 lon/lat[/height]."""
    flat = [p for p in positions if len(p) == 2]
    tall = [p for p in positions if len(p) == 3]
    if flat:
        _transform(flat, _transformer(epsg, False), False)
    if tall:
        _transform(tall, _transformer(epsg, True), True)
    for position in positions:
        _normalise(position)


def _transform(
    positions: Sequence[Position],
    transformer: Optional[Transformer],
    vertical: bool,
) -> None:
    if transformer is None:
        return
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    if vertical:
        zs = [p[2] for p in positions]
        xs, ys, zs = transformer.transform(xs, ys, zs, errcheck=True)
        for position, z in zip(positions, zs):
            position[2] = float(z)
    else:
        xs, ys = transformer.transform(xs, ys, errcheck=True)
    for position, x, y in zip(positions, xs, ys):
        position[0] = float(x)
        position[1] = float(y)


def _normalise(position: Position) -> None:
    """Validate one position and pull it into the documented ranges."""
    for value in position:
        if not math.isfinite(value):
            raise ValueError(
                "coordinate is not a finite number and cannot be written as "
                "JSON: %r" % (position,)
            )
    lon, lat = position[0], position[1]
    if lat > 90.0 or lat < -90.0:
        if lat > 90.0 + _LAT_TOLERANCE or lat < -90.0 - _LAT_TOLERANCE:
            raise ValueError("latitude outside [-90, 90] after reprojection: %r" % lat)
        lat = math.copysign(90.0, lat)  # rounding noise at the pole
    if lon > 180.0 or lon < -180.0:
        lon = ((lon + 180.0) % 360.0) - 180.0
    position[0] = lon
    position[1] = lat


# --------------------------------------------------------------------------
# ring orientation (section 3.1.6)
# --------------------------------------------------------------------------


def _orient(rings: Sequence[Tuple[Ring, bool]]) -> None:
    for coords, counterclockwise in rings:
        area = _signed_area(coords)
        if area != 0.0 and (area > 0.0) != counterclockwise:
            coords.reverse()
        # Reversal preserves closure, but make it exact regardless.
        coords[-1] = list(coords[0])


def _signed_area(ring: Ring) -> float:
    """Shoelace area of a ring in degrees squared; positive if counterclockwise.

    Vertices are shifted to the first one before multiplying so that small
    rings far from the origin do not lose their sign to cancellation.
    """
    x0, y0 = ring[0][0], ring[0][1]
    total = 0.0
    previous = ring[0]
    for current in ring[1:]:
        total += (previous[0] - x0) * (current[1] - y0) - (current[0] - x0) * (
            previous[1] - y0
        )
        previous = current
    return total / 2.0