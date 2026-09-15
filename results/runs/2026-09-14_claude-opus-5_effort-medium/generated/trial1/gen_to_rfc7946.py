"""Convert shapely geometries to RFC 7946 GeoJSON geometry objects.

The single public entry point is :func:`to_rfc7946`.

Conformance notes (RFC 7946):

* Section 4 -- the coordinate reference system of a GeoJSON text is always
  WGS 84 (EPSG:4326) with coordinates in decimal degrees, longitude first.
  The input geometry is therefore reprojected from ``epsg`` with
  ``always_xy=True`` so that the geometry's ``(x, y)`` is read as easting /
  northing (or longitude / latitude) and written out as longitude / latitude,
  regardless of the authority-declared axis order of either CRS.
* Section 3.1.6 -- polygon rings follow the right-hand rule: exterior rings
  are counterclockwise, interior rings (holes) clockwise.
* Section 3.1.1 -- a position is ``[lon, lat]`` or ``[lon, lat, alt]``.  A
  measure (M) value carries no meaning in GeoJSON and is dropped; a Z value is
  passed through as an elevation in meters.  Non-finite values are rejected
  because JSON has no NaN/Infinity literals.
* Section 3.1.8 -- nested GeometryCollections are flattened, and empty members
  of a collection are dropped.
* Section 3.1.9 -- longitudes are wrapped into [-180, 180].  Note that
  geometries crossing the antimeridian are *not* cut into two parts; RFC 7946
  states that cutting SHOULD be done, so such geometries remain valid GeoJSON
  but may be rendered incorrectly by naive consumers.

Geometries that cannot be expressed at all (an empty Point or an empty
LineString, which would require a position / two positions that do not exist)
raise :class:`ValueError` rather than emitting a structure that violates the
specification.
"""

from __future__ import annotations

import math
import operator
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84_EPSG = 4326
_LAT_TOLERANCE = 1e-7


@lru_cache(maxsize=64)
def _transformer(epsg: int) -> Transformer | None:
    """Return a transformer from ``epsg`` to WGS 84, or None if it is a no-op."""
    source = CRS.from_epsg(epsg)
    target = CRS.from_epsg(_WGS84_EPSG)
    if source == target:
        return None
    return Transformer.from_crs(source, target, always_xy=True)


def _project(coords: np.ndarray, transformer: Transformer | None) -> np.ndarray:
    if transformer is None:
        return coords
    if coords.shape[1] >= 3:
        x, y, z = transformer.transform(coords[:, 0], coords[:, 1], coords[:, 2])
        return np.column_stack((x, y, z))
    x, y = transformer.transform(coords[:, 0], coords[:, 1])
    return np.column_stack((x, y))


def _wrap_longitude(lon: float) -> float:
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0
    return wrapped - 180.0


def _position(point, precision: int | None) -> list[float]:
    """Turn a raw (lon, lat[, z]) tuple into an RFC 7946 position array."""
    lon = float(point[0])
    lat = float(point[1])
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(
            "geometry contains a non-finite coordinate after reprojection; "
            "the source coordinates may be outside the area of use of the CRS"
        )
    lon = _wrap_longitude(lon)
    if lat > 90.0:
        if lat - 90.0 > _LAT_TOLERANCE:
            raise ValueError(f"latitude {lat} is out of range after reprojection")
        lat = 90.0
    elif lat < -90.0:
        if -90.0 - lat > _LAT_TOLERANCE:
            raise ValueError(f"latitude {lat} is out of range after reprojection")
        lat = -90.0

    position = [lon, lat]
    if len(point) > 2:
        z = float(point[2])
        if math.isfinite(z):
            position.append(z)

    if precision is not None:
        position = [round(value, precision) for value in position]
    # Avoid emitting "-0.0", which is valid JSON but needlessly surprising.
    return [value + 0.0 for value in position]


def _coords(geom) -> list[tuple]:
    return [tuple(point) for point in geom.coords]


def _signed_area(ring: list[tuple]) -> float:
    """Shoelace area of a closed ring; positive means counterclockwise."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(
        ((p[0], p[1]) for p in ring), ((p[0], p[1]) for p in ring[1:])
    ):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _ring(linear_ring, ccw: bool, precision: int | None) -> list[list[float]]:
    points = _coords(linear_ring)
    if points and points[0] != points[-1]:
        points.append(points[0])
    if len(points) < 4:
        raise ValueError("a linear ring must have four or more positions")
    area = _signed_area(points)
    if area != 0.0 and (area > 0.0) != ccw:
        points.reverse()
    return [_position(point, precision) for point in points]


def _geometry(geom, precision: int | None) -> dict:
    kind = geom.geom_type

    if kind == "Point":
        if geom.is_empty:
            raise ValueError(
                "an empty Point cannot be represented as an RFC 7946 geometry"
            )
        return {"type": "Point", "coordinates": _position(_coords(geom)[0], precision)}

    if kind in ("LineString", "LinearRing"):
        points = _coords(geom)
        if len(points) < 2:
            raise ValueError(
                "an empty LineString cannot be represented as an RFC 7946 geometry"
            )
        return {
            "type": "LineString",
            "coordinates": [_position(point, precision) for point in points],
        }

    if kind == "Polygon":
        if geom.is_empty:
            return {"type": "Polygon", "coordinates": []}
        rings = [_ring(geom.exterior, True, precision)]
        rings.extend(_ring(hole, False, precision) for hole in geom.interiors)
        return {"type": "Polygon", "coordinates": rings}

    if kind == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [
                _position(_coords(part)[0], precision)
                for part in geom.geoms
                if not part.is_empty
            ],
        }

    if kind == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [
                [_position(point, precision) for point in _coords(part)]
                for part in geom.geoms
                if not part.is_empty
            ],
        }

    if kind == "MultiPolygon":
        polygons = []
        for part in geom.geoms:
            if part.is_empty:
                continue
            rings = [_ring(part.exterior, True, precision)]
            rings.extend(_ring(hole, False, precision) for hole in part.interiors)
            polygons.append(rings)
        return {"type": "MultiPolygon", "coordinates": polygons}

    if kind == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": _flatten(geom, precision)}

    raise TypeError(f"unsupported geometry type: {kind!r}")


def _flatten(collection, precision: int | None) -> list[dict]:
    """Inline nested collections; RFC 7946 says to avoid them."""
    members: list[dict] = []
    for part in collection.geoms:
        if part.is_empty and part.geom_type in (
            "Point",
            "LineString",
            "LinearRing",
            "GeometryCollection",
        ):
            continue
        if part.geom_type == "GeometryCollection":
            members.extend(_flatten(part, precision))
        else:
            members.append(_geometry(part, precision))
    return members


def to_rfc7946(geom, epsg, *, precision: int | None = None) -> dict:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in the CRS given by
        ``epsg``, with ``x`` as the first ordinate (easting / longitude).
    epsg:
        Integer EPSG code of that CRS, e.g. ``4326`` or ``3857``.  The geometry
        is reprojected to WGS 84 longitude / latitude as RFC 7946 requires.
    precision:
        Optional number of decimal places to round each ordinate to.  ``None``
        (the default) keeps full double precision; ``6`` is roughly 0.1 m of
        longitude at the equator and is a common size/precision trade-off.

    Returns
    -------
    dict
        A geometry object with ``type`` and ``coordinates`` members (or
        ``type`` and ``geometries`` for a GeometryCollection), containing only
        JSON-native types and therefore directly serializable with
        :func:`json.dumps`.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    try:
        epsg = operator.index(epsg)
    except TypeError:
        raise TypeError(
            f"expected an integer EPSG code, got {type(epsg).__name__}"
        ) from None
    if precision is not None:
        precision = operator.index(precision)

    transformer = _transformer(epsg)

    # Round-tripping through shapely.transform both reprojects the coordinates
    # in a single vectorized call and normalizes the dimensionality: M values
    # are dropped (they have no GeoJSON representation) and Z values are kept
    # only when the input actually carries them.
    include_z = bool(shapely.has_z(geom))
    geom = shapely.transform(
        geom,
        lambda coords: _project(coords, transformer),
        include_z=include_z,
        include_m=False,
    )

    return _geometry(geom, precision)